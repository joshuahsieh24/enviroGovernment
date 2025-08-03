from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
from pydantic import BaseModel, Field
from enum import Enum

class SourceType(str, Enum):
    CSV = "csv"
    PDF = "pdf"
    JSON = "json"
    XML = "xml"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ESRSStandard(str, Enum):
    E1 = "E1"  # Climate change
    E2 = "E2"  # Pollution
    E3 = "E3"  # Water and marine resources
    E4 = "E4"  # Biodiversity and ecosystems
    E5 = "E5"  # Resource use and circular economy
    S1 = "S1"  # Own workforce
    S2 = "S2"  # Workers in the value chain
    S3 = "S3"  # Affected communities
    S4 = "S4"  # Consumers and end-users
    G1 = "G1"  # Business conduct

class EvidenceItem(BaseModel):
    """Model for ESG evidence items"""
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str
    source_type: SourceType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    # Processing results
    extracted_data: Optional[Dict[str, Any]] = None
    esrs_mapping: Optional[Dict[str, Any]] = None
    gaps: Optional[Dict[str, Any]] = None
    narrative: Optional[str] = None
    vector_id: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True

class ESRSMetric(BaseModel):
    """Model for ESRS metrics"""
    metric_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    standard: ESRSStandard
    metric_name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    data_source: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
class GapAnalysis(BaseModel):
    """Model for gap analysis results"""
    gap_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    evidence_id: str
    gap_type: str  # "missing_standard", "incomplete_data", "outdated_data"
    standard: ESRSStandard
    description: str
    priority: str  # "high", "medium", "low"
    recommended_action: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

class NarrativeReport(BaseModel):
    """Model for narrative reports"""
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    evidence_id: str
    content: str
    summary: Optional[str] = None
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    vector_id: Optional[str] = None

class AlertConfig(BaseModel):
    """Model for alert configurations"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    conditions: Dict[str, Any]  # JSON conditions for triggering alerts
    channels: List[str] = Field(default_factory=list)  # ["slack", "email", "sns"]
    recipients: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

# DynamoDB table schemas
EVIDENCE_TABLE_SCHEMA = {
    "TableName": "esg-evidence",
    "KeySchema": [
        {"AttributeName": "evidence_id", "KeyType": "HASH"}
    ],
    "AttributeDefinitions": [
        {"AttributeName": "evidence_id", "AttributeType": "S"},
        {"AttributeName": "status", "AttributeType": "S"},
        {"AttributeName": "created_at", "AttributeType": "S"}
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "status-created-index",
            "KeySchema": [
                {"AttributeName": "status", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"}
            ],
            "Projection": {"ProjectionType": "ALL"}
        }
    ]
}

METRICS_TABLE_SCHEMA = {
    "TableName": "esg-metrics",
    "KeySchema": [
        {"AttributeName": "metric_id", "KeyType": "HASH"}
    ],
    "AttributeDefinitions": [
        {"AttributeName": "metric_id", "AttributeType": "S"},
        {"AttributeName": "standard", "AttributeType": "S"},
        {"AttributeName": "last_updated", "AttributeType": "S"}
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "standard-updated-index",
            "KeySchema": [
                {"AttributeName": "standard", "KeyType": "HASH"},
                {"AttributeName": "last_updated", "KeyType": "RANGE"}
            ],
            "Projection": {"ProjectionType": "ALL"}
        }
    ]
}

GAPS_TABLE_SCHEMA = {
    "TableName": "esg-gaps",
    "KeySchema": [
        {"AttributeName": "gap_id", "KeyType": "HASH"}
    ],
    "AttributeDefinitions": [
        {"AttributeName": "gap_id", "AttributeType": "S"},
        {"AttributeName": "priority", "AttributeType": "S"},
        {"AttributeName": "created_at", "AttributeType": "S"}
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "priority-created-index",
            "KeySchema": [
                {"AttributeName": "priority", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"}
            ],
            "Projection": {"ProjectionType": "ALL"}
        }
    ]
}