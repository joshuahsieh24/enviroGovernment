# backend/main.py

import json
import json
import boto3
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
from agent.graph import ESGWorkflow
from db.models import EvidenceItem
import os
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ESG Insight Hub API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS clients
stepfunctions = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')

# Environment variables
STEP_FUNCTION_ARN = os.environ.get('STEP_FUNCTION_ARN')
EVIDENCE_TABLE = os.environ.get('EVIDENCE_TABLE', 'esg-evidence')

class EvidenceRequest(BaseModel):
    file_path: str
    source_type: str  # 'csv', 'pdf', 'json'
    metadata: Optional[Dict[str, Any]] = {}

class HealthResponse(BaseModel):
    status: str
    version: str

class ComplianceMetrics(BaseModel):
    environmental: int
    social: int
    governance: int
    reporting: int

class Alert(BaseModel):
    id: int
    type: str
    title: str
    message: str
    time: str
    priority: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", version="1.0.0")

@app.get("/api/dashboard/metrics")
async def get_dashboard_metrics():
    """Get dashboard key metrics"""
    return {
        "compliance_score": 87,
        "documents_processed": 156,
        "alerts_count": 3,
        "gaps_identified": 12
    }

@app.get("/api/compliance/metrics", response_model=ComplianceMetrics)
async def get_compliance_metrics():
    """Get CSRD compliance metrics"""
    return ComplianceMetrics(
        environmental=85,
        social=72,
        governance=91,
        reporting=78
    )

@app.get("/api/alerts", response_model=List[Alert])
async def get_alerts():
    """Get current alerts"""
    return [
        Alert(
            id=1,
            type="warning",
            title="ESRS E2 Compliance Gap",
            message="Pollution metrics missing for Q3 2024",
            time="2 hours ago",
            priority="High"
        ),
        Alert(
            id=2,
            type="error",
            title="Document Expiry Alert",
            message="Sustainability report expires in 15 days",
            time="1 day ago",
            priority="Critical"
        ),
        Alert(
            id=3,
            type="info",
            title="New CSRD Requirement",
            message="ESRS S2 implementation due next month",
            time="3 days ago",
            priority="Medium"
        )
    ]

@app.post("/v1/evidence")
async def process_evidence(request: EvidenceRequest, background_tasks: BackgroundTasks):
    """
    Process uploaded evidence through the ESG workflow
    """
    try:
        # Validate input
        if not request.file_path:
            raise HTTPException(status_code=400, detail="file_path is required")
        
        # Create evidence item
        evidence = EvidenceItem(
            file_path=request.file_path,
            source_type=request.source_type,
            metadata=request.metadata or {}
        )
        
        # Start Step Function execution
        step_input = {
            "evidence_id": evidence.evidence_id,
            "file_path": request.file_path,
            "source_type": request.source_type,
            "metadata": request.metadata or {}
        }
        
        response = stepfunctions.start_execution(
            stateMachineArn=STEP_FUNCTION_ARN,
            name=f"esg-processing-{evidence.evidence_id}",
            input=json.dumps(step_input)
        )
        
        logger.info(f"Started Step Function execution: {response['executionArn']}")
        
        return {
            "message": "Evidence processing started",
            "evidence_id": evidence.evidence_id,
            "execution_arn": response['executionArn']
        }
        
    except Exception as e:
        logger.error(f"Error processing evidence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/evidence/{evidence_id}")
async def get_evidence(evidence_id: str):
    """
    Retrieve evidence processing status and results
    """
    try:
        table = dynamodb.Table(EVIDENCE_TABLE)
        response = table.get_item(Key={'evidence_id': evidence_id})
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Evidence not found")
        
        return response['Item']
        
    except Exception as e:
        logger.error(f"Error retrieving evidence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/gaps")
async def get_gaps():
    """
    Retrieve current ESG gaps and expiring artifacts
    """
    try:
        table = dynamodb.Table(EVIDENCE_TABLE)
        
        # Scan for items with gaps or expiring artifacts
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('gaps').exists() |
                           boto3.dynamodb.conditions.Attr('expiring_artifacts').exists()
        )
        
        return {
            "gaps": response.get('Items', []),
            "count": response.get('Count', 0)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving gaps: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)