import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from backend.agent.graph import ESGWorkflow, ESGWorkflowState
from backend.agent.tools import ESGTools
from backend.db.models import EvidenceItem, SourceType
import boto3
from moto import mock_dynamodb, mock_s3, mock_sns

@pytest.fixture
def mock_esg_tools():
    """Mock ESG tools for testing"""
    with patch('backend.agent.graph.ESGTools') as mock_tools:
        tools_instance = Mock()
        mock_tools.return_value = tools_instance
        
        # Mock tool methods
        tools_instance.extract_data_from_file.return_value = {
            "data_type": "tabular",
            "rows": 100,
            "columns": ["energy_consumption", "co2_emissions"],
            "data": [{"energy_consumption": 1000, "co2_emissions": 500}]
        }
        
        tools_instance.map_to_esrs_metrics.return_value = {
            "mapped_standards": ["E1"],
            "metrics": [{"name": "GHG emissions", "value": 500, "unit": "tCO2e"}],
            "data_quality": "high",
            "missing_info": [],
            "confidence": 0.9
        }
        
        tools_instance.identify_gaps.return_value = {
            "gaps": [{
                "type": "missing_standard",
                "standard": "E2",
                "priority": "high"
            }],
            "expiring_artifacts": [],
            "gap_count": 1,
            "expiring_count": 0
        }
        
        tools_instance.generate_narrative.return_value = "ESG performance summary..."
        tools_instance.store_in_vector_db.return_value = "vec_123"
        
        yield tools_instance

@pytest.fixture
def workflow_state():
    """Create a test workflow state"""
    state = ESGWorkflowState()
    state.evidence_id = "test-evidence-123"
    state.file_path = "test/sample.csv"
    state.source_type = "csv"
    state.metadata = {"source": "test"}
    return state

@pytest.fixture
def esg_workflow(mock_esg_tools):
    """Create ESG workflow instance with mocked dependencies"""
    with patch('boto3.resource'), patch('boto3.client'):
        workflow = ESGWorkflow()
        workflow.tools = mock_esg_tools
        return workflow

@mock_dynamodb
@mock_s3
@mock_sns
class TestESGWorkflow:
    """Test cases for ESG workflow"""
    
    def setup_method(self):
        """Set up test environment"""
        # Create mock AWS resources
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.s3 = boto3.client('s3', region_name='us-east-1')
        self.sns = boto3.client('sns', region_name='us-east-1')
        
        # Create test table
        self.dynamodb.create_table(
            TableName='esg-evidence',
            KeySchema=[{'AttributeName': 'evidence_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'evidence_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create test bucket
        self.s3.create_bucket(Bucket='esg-insight-data')
        
        # Create SNS topic
        response = self.sns.create_topic(Name='esg-alerts')
        self.topic_arn = response['TopicArn']
    
    def test_ingest_node_success(self, esg_workflow, workflow_state):
        """Test successful ingestion node"""
        result = esg_workflow.ingest_node(workflow_state)
        
        assert result.status == "ingesting"
        assert len(result.errors) == 0
        assert result.evidence_id == "test-evidence-123"
    
    def test_ingest_node_missing_file_path(self, esg_workflow):
        """Test ingestion node with missing file path"""
        state = ESGWorkflowState()
        state.evidence_id = "test-123"
        state.source_type = "csv"
        
        result = esg_workflow.ingest_node(state)
        
        assert result.status == "error"
        assert len(result.errors) == 1
        assert "file_path is required" in result.errors[0]
    
    def test_extract_node_success(self, esg_workflow, workflow_state, mock_esg_tools):
        """Test successful data extraction"""
        result = esg_workflow.extract_node(workflow_state)
        
        assert result.status == "extracting"
        assert result.extracted_data is not None
        assert result.extracted_data["data_type"] == "tabular"
        mock_esg_tools.extract_data_from_file.assert_called_once_with("test/sample.csv", "csv")
    
    def test_extract_node_failure(self, esg_workflow, workflow_state, mock_esg_tools):
        """Test data extraction failure"""
        mock_esg_tools.extract_data_from_file.side_effect = Exception("File not found")
        
        result = esg_workflow.extract_node(workflow_state)
        
        assert result.status == "error"
        assert len(result.errors) == 1
        assert "File not found" in result.errors[0]
    
    def test_map_esrs_node_success(self, esg_workflow, workflow_state, mock_esg_tools):
        """Test successful ESRS mapping"""
        workflow_state.extracted_data = {"data_type": "tabular"}
        
        result = esg_workflow.map_esrs_node(workflow_state)
        
        assert result.status == "mapping"
        assert result.esrs_mapping is not None
        assert "E1" in result.esrs_mapping["mapped_standards"]
        mock_esg_tools.map_to_esrs_metrics.assert_called_once()
    
    def test_gap_check_node_success(self, esg_workflow, workflow_state, mock_esg_tools):
        """Test successful gap analysis"""
        workflow_state.esrs_mapping = {"mapped_standards": ["E1"]}
        
        result = esg_workflow.gap_check_node(workflow_state)
        
        assert result.status == "gap_checking"
        assert result.gaps is not None
        assert result.gaps["gap_count"] == 1
        mock_esg_tools.identify_gaps.assert_called_once()
    
    def test_narrative_draft_node_success(self, esg_workflow, workflow_state, mock_esg_tools):
        """Test successful narrative generation"""
        workflow_state.esrs_mapping = {"mapped_standards": ["E1"]}
        workflow_state.gaps = {"gaps": []}
        
        result = esg_workflow.narrative_draft_node(workflow_state)
        
        assert result.status == "generating_narrative"
        assert result.narrative == "ESG performance summary..."
        assert result.vector_id == "vec_123"
        mock_esg_tools.generate_narrative.assert_called_once()
        mock_esg_tools.store_in_vector_db.assert_called_once()
    
    @patch('boto3.resource')
    def test_persist_node_success(self, mock_dynamodb_resource, esg_workflow, workflow_state):
        """Test successful data persistence"""
        # Mock DynamoDB table
        mock_table = Mock()
        mock_dynamodb_resource.return_value.Table.return_value = mock_table
        
        # Set up state
        workflow_state.extracted_data = {"data_type": "tabular"}
        workflow_state.esrs_mapping = {"mapped_standards": ["E1"]}
        workflow_state.gaps = {"gaps": []}
        workflow_state.narrative = "Test narrative"
        workflow_state.vector_id = "vec_123"
        
        result = esg_workflow.persist_node(workflow_state)
        
        assert result.status == "completed"
        mock_table.put_item.assert_called_once()
        
        # Verify the item structure
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        assert item['evidence_id'] == "test-evidence-123"
        assert item['status'] == 'completed'
        assert 'processed_at' in item
    
    @patch('boto3.client')
    def test_notify_node_with_critical_gaps(self, mock_sns_client, esg_workflow, workflow_state):
        """Test notification for critical gaps"""
        # Mock SNS client
        mock_sns = Mock()
        mock_sns_client.return_value = mock_sns
        
        # Set up state with critical gaps
        workflow_state.gaps = {
            "gaps": [{
                "type": "missing_standard",
                "standard": "E2",
                "priority": "high"
            }],
            "expiring_artifacts": []
        }
        workflow_state.narrative = "Test narrative summary"
        
        result = esg_workflow.notify_node(workflow_state)
        
        # Verify SNS publish was called
        mock_sns.publish.assert_called_once()
        call_args = mock_sns.publish.call_args
        assert "Critical gaps found" in call_args[1]['Subject']
    
    @patch('boto3.client')
    def test_notify_node_no_critical_gaps(self, mock_sns_client, esg_workflow, workflow_state):
        """Test notification with no critical gaps"""
        mock_sns = Mock()
        mock_sns_client.return_value = mock_sns
        
        # Set up state with no critical gaps
        workflow_state.gaps = {
            "gaps": [{
                "type": "missing_standard",
                "standard": "E2",
                "priority": "low"
            }],
            "expiring_artifacts": []
        }
        
        result = esg_workflow.notify_node(workflow_state)
        
        # Verify SNS publish was not called
        mock_sns.publish.assert_not_called()
    
    @patch('boto3.resource')
    @patch('boto3.client')
    def test_error_handler_node(self, mock_sns_client, mock_dynamodb_resource, esg_workflow, workflow_state):
        """Test error handling node"""
        mock_table = Mock()
        mock_dynamodb_resource.return_value.Table.return_value = mock_table
        mock_sns = Mock()
        mock_sns_client.return_value = mock_sns
        
        # Set up error state
        workflow_state.errors = ["Test error 1", "Test error 2"]
        
        result = esg_workflow.error_handler_node(workflow_state)
        
        assert result.status == "failed"
        mock_table.put_item.assert_called_once()
        mock_sns.publish.assert_called_once()
        
        # Verify error message
        call_args = mock_sns.publish.call_args
        assert "ESG Processing Failed" in call_args[1]['Subject']
    
    def test_should_continue_with_errors(self, esg_workflow):
        """Test should_continue method with errors"""
        state = ESGWorkflowState()
        state.errors = ["Some error"]
        
        result = esg_workflow.should_continue(state)
        assert result == "error"
    
    def test_should_continue_without_errors(self, esg_workflow):
        """Test should_continue method without errors"""
        state = ESGWorkflowState()
        
        result = esg_workflow.should_continue(state)
        assert result == "continue"

@pytest.mark.integration
class TestESGWorkflowIntegration:
    """Integration tests for the full workflow"""
    
    @patch('backend.agent.tools.ESGTools')
    @patch('boto3.resource')
    @patch('boto3.client')
    def test_full_workflow_success(self, mock_client, mock_resource, mock_tools):
        """Test complete workflow execution"""
        # Mock all dependencies
        mock_tools_instance = Mock()
        mock_tools.return_value = mock_tools_instance
        
        # Set up tool responses
        mock_tools_instance.extract_data_from_file.return_value = {"data_type": "tabular"}
        mock_tools_instance.map_to_esrs_metrics.return_value = {"mapped_standards": ["E1"]}
        mock_tools_instance.identify_gaps.return_value = {"gaps": [], "expiring_artifacts": []}
        mock_tools_instance.generate_narrative.return_value = "Summary"
        mock_tools_instance.store_in_vector_db.return_value = "vec_123"
        
        # Mock AWS resources
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_sns = Mock()
        mock_client.return_value = mock_sns
        
        # Create workflow and run
        workflow = ESGWorkflow()
        input_data = {
            "evidence_id": "test-123",
            "file_path": "test.csv",
            "source_type": "csv",
            "metadata": {}
        }
        
        result = workflow.run_workflow(input_data)
        
        assert result["status"] == "completed"
        assert result["evidence_id"] == "test-123"
        assert len(result["errors"]) == 0

if __name__ == "__main__":
    pytest.main([__file__])