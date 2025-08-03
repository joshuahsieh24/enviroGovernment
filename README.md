# ESG Insight Hub

A serverless platform that ingests raw sustainability evidence, maps it to CSRD/ESRS metrics, identifies gaps/expiring artifacts, drafts narrative text, and alerts stakeholders.

## 🏗️ Architecture
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   n8n Webhook   │───▶│    S3 Raw    │───▶│  Lambda Ingest  │
└─────────────────┘    └──────────────┘    └─────────────────┘
│
▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Step Functions  │◀───│ EventBridge  │◀───│   API Gateway   │
└─────────────────┘    └──────────────┘    └─────────────────┘
│
▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   LangGraph     │───▶│  DynamoDB    │───▶│   QuickSight    │
│   Workflow      │    │   Tables     │    │   Dashboard     │
└─────────────────┘    └──────────────┘    └─────────────────┘
│
▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│  OpenSearch     │    │   S3 Data    │    │      SNS        │
│   Vectorize     │    │   Parquet    │    │   Alerts        │
└─────────────────┘    └──────────────┘    └─────────────────┘
│                                           │
▼                                           ▼
┌─────────────────┐                        ┌─────────────────┐
│    Bedrock      │                        │  Slack/Email    │
│ Claude/AI21     │                        │     n8n         │
└─────────────────┘                        └─────────────────┘

## 🚀 Setup Guide

### Prerequisites
- AWS CLI configured with appropriate permissions
- Node.js 18+ and npm
- Python 3.10+
- Docker (for local testing)

### Deployment Steps

1. **Install Dependencies**
   ```bash
   npm install -g aws-cdk
   cd iaac && npm install
   cd ../backend && pip install -r requirements.txt

Bootstrap CDK
bashcdk bootstrap

Deploy Infrastructure
bashcd iaac
cdk deploy --all

Configure n8n Workflows

Import n8n/ingest_flow.json and n8n/alert_flow.json
Set webhook URLs and credentials



💰 Cost Estimate (Monthly)
ServiceUsageCostLambda10 runs/day × 30s avg$2.50Step Functions300 executions$1.50DynamoDB1GB storage + reads$3.00S35GB storage$0.12OpenSearch Serverless1 OCU$15.00Bedrock100K tokens/day$25.00API Gateway300 requests$0.35Total$47.47
🎯 KPI Targets

Data Ingestion: 99.5% success rate
Processing Latency: <30 seconds p95
Gap Detection: 95% accuracy
Cost Efficiency: <$50/month
Availability: 99.9% uptime

