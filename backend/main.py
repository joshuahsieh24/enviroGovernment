 ## backend/main.py

```python
import json
import boto3
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
from agent.graph import ESGWorkflow
from db.models import EvidenceItem
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ESG Insight Hub API", version="1.0.0")

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

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", version="1.0.0")

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