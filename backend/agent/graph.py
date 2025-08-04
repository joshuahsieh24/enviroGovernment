import json
from typing import Dict, Any, List
from datetime import datetime
import boto3
import logging
from langchain.schema import BaseMessage
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from .tools import ESGTools
from db.models import EvidenceItem

logger = logging.getLogger(__name__)

class ESGWorkflowState:
    """State management for ESG workflow"""
    
    def __init__(self):
        self.evidence_id: str = ""
        self.file_path: str = ""
        self.source_type: str = ""
        self.metadata: Dict[str, Any] = {}
        self.extracted_data: Dict[str, Any] = {}
        self.esrs_mapping: Dict[str, Any] = {}
        self.gaps: Dict[str, Any] = {}
        self.narrative: str = ""
        self.vector_id: str = ""
        self.errors: List[str] = []
        self.status: str = "started"

class ESGWorkflow:
    """LangGraph workflow for ESG processing"""
    
    def __init__(self):
        self.tools = ESGTools()
        self.dynamodb = boto3.resource('dynamodb')
        self.sns = boto3.client('sns')
        self.evidence_table = "esg-evidence"
        self.sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:esg-alerts"
    
    def create_graph(self):
        """Create the LangGraph workflow"""
        from langgraph import StateGraph
        
        workflow = StateGraph(ESGWorkflowState)
        
        # Add nodes
        workflow.add_node("ingest", self.ingest_node)
        workflow.add_node("extract", self.extract_node)
        workflow.add_node("map_esrs", self.map_esrs_node)
        workflow.add_node("gap_check", self.gap_check_node)
        workflow.add_node("narrative_draft", self.narrative_draft_node)
        workflow.add_node("persist", self.persist_node)
        workflow.add_node("notify", self.notify_node)
        workflow.add_node("error_handler", self.error_handler_node)
        
        # Define edges
        workflow.set_entry_point("ingest")
        workflow.add_edge("ingest", "extract")
        workflow.add_edge("extract", "map_esrs")
        workflow.add_edge("map_esrs", "gap_check")
        workflow.add_edge("gap_check", "narrative_draft")
        workflow.add_edge("narrative_draft", "persist")
        workflow.add_edge("persist", "notify")
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "extract",
            self.should_continue,
            {
                "continue": "map_esrs",
                "error": "error_handler"
            }
        )
        
        return workflow.compile()
    
    def should_continue(self, state: ESGWorkflowState) -> str:
        """Determine if workflow should continue or handle errors"""
        if state.errors:
            return "error"
        return "continue"
    
    def ingest_node(self, state: ESGWorkflowState) -> ESGWorkflowState:
        """Initial ingestion node"""
        try:
            logger.info(f"Starting ingestion for evidence: {state.evidence_id}")
            state.status = "ingesting"
            
            # Validate inputs
            if not state.file_path:
                raise ValueError("file_path is required")
            
            if not state.source_type:
                raise ValueError("source_type is required")
            
            logger.info(f"Ingestion completed for {state.evidence_id}")
            return state
            
        except Exception as e:
            logger.error(f"Ingestion failed: {str(e)}")
            state.errors.append(f"Ingestion error: {str(e)}")
            state.status = "error"
            return state
    
    def extract_node(self, state: ESGWorkflowState) -> ESGWorkflowState:
        """Extract data from the uploaded file"""
        try:
            logger.info(f"Extracting data from {state.file_path}")
            state.status = "extracting"
            
            # Extract data using tools
            extracted_data = self.tools.extract_data_from_file(
                state.file_path, 
                state.source_type
            )
            
            state.extracted_data = extracted_data
            logger.info(f"Data extraction completed for {state.evidence_id}")
            return state
            
        except Exception as e:
            logger.error(f"Data extraction failed: {str(e)}")
            state.errors.append(f"Extraction error: {str(e)}")
            state.status = "error"
            return state
    
    def map_esrs_node(self, state: ESGWorkflowState) -> ESGWorkflowState:
        """Map extracted data to ESRS metrics"""
        try:
            logger.info(f"Mapping to ESRS metrics for {state.evidence_id}")
            state.status = "mapping"
            
            # Map to ESRS using LLM
            esrs_mapping = self.tools.map_to_esrs_metrics(state.extracted_data)
            state.esrs_mapping = esrs_mapping
            
            logger.info(f"ESRS mapping completed for {state.evidence_id}")
            return state
            
        except Exception as e:
            logger.error(f"ESRS mapping failed: {str(e)}")
            state.errors.append(f"ESRS mapping error: {str(e)}")
            state.status = "error"
            return state
    
    def gap_check_node(self, state: ESGWorkflowState) -> ESGWorkflowState:
        """Check for gaps in ESG coverage"""
        try:
            logger.info(f"Checking gaps for {state.evidence_id}")
            state.status = "gap_checking"
            
            # Identify gaps
            gaps = self.tools.identify_gaps(state.esrs_mapping)
            state.gaps = gaps
            
            logger.info(f"Gap analysis completed for {state.evidence_id}")
            return state
            
        except Exception as e:
            logger.error(f"Gap analysis failed: {str(e)}")
            state.errors.append(f"Gap analysis error: {str(e)}")
            state.status = "error"
            return state
    
    def narrative_draft_node(self, state: ESGWorkflowState) -> ESGWorkflowState:
        """Generate narrative summary"""
        try:
            logger.info(f"Generating narrative for {state.evidence_id}")
            state.status = "generating_narrative"
            
            # Generate narrative
            narrative = self.tools.generate_narrative(
                state.esrs_mapping, 
                state.gaps
            )
            state.narrative = narrative
            
            # Store in vector database for future reference
            vector_id = self.tools.store_in_vector_db(
                narrative, 
                {"evidence_id": state.evidence_id, "type": "narrative"}
            )
            state.vector_id = vector_id
            
            logger.info(f"Narrative generation completed for {state.evidence_id}")
            return state
            
        except Exception as e:
            logger.error(f"Narrative generation failed: {str(e)}")
            state.errors.append(f"Narrative generation error: {str(e)}")
            state.status = "error"
            return state
    
    def persist_node(self, state: ESGWorkflowState) -> ESGWorkflowState:
        """Persist results to DynamoDB"""
        try:
            logger.info(f"Persisting results for {state.evidence_id}")
            state.status = "persisting"
            
            table = self.dynamodb.Table(self.evidence_table)
            
            # Create evidence item
            evidence_item = {
                'evidence_id': state.evidence_id,
                'file_path': state.file_path,
                'source_type': state.source_type,
                'metadata': state.metadata,
                'extracted_data': state.extracted_data,
                'esrs_mapping': state.esrs_mapping,
                'gaps': state.gaps,
                'narrative': state.narrative,
                'vector_id': state.vector_id,
                'status': 'completed',
                'processed_at': datetime.now().isoformat(),
                'errors': state.errors
            }
            
            # Store in DynamoDB
            table.put_item(Item=evidence_item)
            
            state.status = "completed"
            logger.info(f"Results persisted for {state.evidence_id}")
            return state
            
        except Exception as e:
            logger.error(f"Persistence failed: {str(e)}")
            state.errors.append(f"Persistence error: {str(e)}")
            state.status = "error"
            return state
    
    def notify_node(self, state: ESGWorkflowState) -> ESGWorkflowState:
        """Send notifications for gaps and alerts"""
        try:
            logger.info(f"Sending notifications for {state.evidence_id}")
            
            # Check if there are critical gaps to notify about
            critical_gaps = [
                gap for gap in state.gaps.get('gaps', [])
                if gap.get('priority') == 'high'
            ]
            
            expiring_artifacts = state.gaps.get('expiring_artifacts', [])
            
            if critical_gaps or expiring_artifacts:
                message = {
                    "evidence_id": state.evidence_id,
                    "critical_gaps": len(critical_gaps),
                    "expiring_artifacts": len(expiring_artifacts),
                    "narrative_summary": state.narrative[:200] + "..." if len(state.narrative) > 200 else state.narrative,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Send SNS notification
                self.sns.publish(
                    TopicArn=self.sns_topic_arn,
                    Message=json.dumps(message),
                    Subject=f"ESG Alert: Critical gaps found in {state.evidence_id}"
                )
                
                logger.info(f"Critical gap notification sent for {state.evidence_id}")
            
            logger.info(f"Notification processing completed for {state.evidence_id}")
            return state
            
        except Exception as e:
            logger.error