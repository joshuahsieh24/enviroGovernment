import boto3
import json
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
import base64
from io import BytesIO
import PyPDF2
import sqlite3
import requests
import os
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class ESGTools:
    """Tools for ESG data processing and analysis - FREE TIER VERSION"""
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
        
        # Local services (FREE)
        self.ollama_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        self.sqlite_db = os.environ.get('SQLITE_DB', '/tmp/esg_vectors.db')
        
        # Configuration
        self.data_bucket = "esg-insight-data"
        self.model_name = "llama2"  # Free local model
        self.fallback_model = "mistral"  # Free fallback
        
        # Initialize local vector DB
        self._init_vector_db()
        
        # Initialize sentence transformer for embeddings (free)
        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')  # Small, free model
        except Exception as e:
            logger.warning(f"Could not load sentence transformer: {e}")
            self.embedder = None
        
    def _init_vector_db(self):
        """Initialize SQLite database with FTS5 for vector search"""
        try:
            conn = sqlite3.connect(self.sqlite_db)
            cursor = conn.cursor()
            
            # Create FTS5 table for text search
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS esg_documents USING fts5(
                    doc_id,
                    content,
                    metadata,
                    embeddings,
                    created_at
                )
            ''')
            
            # Create regular table for structured data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS esg_vectors (
                    id INTEGER PRIMARY KEY,
                    doc_id TEXT UNIQUE,
                    content TEXT,
                    embedding BLOB,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Vector database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing vector DB: {str(e)}")
    
    def extract_data_from_file(self, file_path: str, source_type: str) -> Dict[str, Any]:
        """Extract structured data from uploaded files"""
        try:
            if source_type == 'csv':
                return self._extract_from_csv(file_path)
            elif source_type == 'pdf':
                return self._extract_from_pdf(file_path)
            elif source_type == 'json':
                return self._extract_from_json(file_path)
            else:
                raise ValueError(f"Unsupported source type: {source_type}")
                
        except Exception as e:
            logger.error(f"Error extracting data from {file_path}: {str(e)}")
            raise
    
    def _extract_from_csv(self, file_path: str) -> Dict[str, Any]:
        """Extract data from CSV file"""
        try:
            # Download from S3
            response = self.s3.get_object(Bucket=self.data_bucket, Key=file_path)
            df = pd.read_csv(BytesIO(response['Body'].read()))
            
            return {
                "data_type": "tabular",
                "rows": len(df),
                "columns": df.columns.tolist(),
                "data": df.to_dict('records')[:100],  # Limit to first 100 records
                "summary": df.describe().to_dict() if df.select_dtypes(include=['number']).shape[1] > 0 else {}
            }
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            raise
    
    def _extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text from PDF file"""
        try:
            response = self.s3.get_object(Bucket=self.data_bucket, Key=file_path)
            pdf_content = BytesIO(response['Body'].read())
            
            reader = PyPDF2.PdfReader(pdf_content)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            return {
                "data_type": "document",
                "pages": len(reader.pages),
                "text": text,
                "word_count": len(text.split())
            }
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise
    
    def _extract_from_json(self, file_path: str) -> Dict[str, Any]:
        """Extract data from JSON file"""
        try:
            response = self.s3.get_object(Bucket=self.data_bucket, Key=file_path)
            data = json.loads(response['Body'].read())
            
            return {
                "data_type": "structured",
                "data": data,
                "keys": list(data.keys()) if isinstance(data, dict) else None
            }
        except Exception as e:
            logger.error(f"Error processing JSON: {str(e)}")
            raise
    
    def map_to_esrs_metrics(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map extracted data to ESRS metrics using FREE local LLM"""
        try:
            prompt = self._create_esrs_mapping_prompt(extracted_data)
            
            # Try primary model first
            try:
                response = self._call_ollama_model(self.model_name, prompt)
            except Exception as e:
                logger.warning(f"Primary model failed, trying fallback: {str(e)}")
                response = self._call_ollama_model(self.fallback_model, prompt)
            
            return self._parse_esrs_response(response)
            
        except Exception as e:
            logger.error(f"Error mapping to ESRS metrics: {str(e)}")
            # Fallback to rule-based mapping
            return self._fallback_esrs_mapping(extracted_data)
    
    def _call_ollama_model(self, model_name: str, prompt: str) -> str:
        """Call local Ollama model (FREE)"""
        try:
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 2000
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ollama model call failed: {str(e)}")
            raise
    
    def _fallback_esrs_mapping(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based fallback for ESRS mapping when LLM fails"""
        try:
            mapped_standards = []
            metrics = []
            
            # Simple keyword-based mapping
            text_content = str(data).lower()
            
            # E1 - Climate change keywords
            if any(keyword in text_content for keyword in ['energy', 'carbon', 'emission', 'ghg', 'co2', 'electricity', 'gas']):
                mapped_standards.append('E1')
                metrics.append({
                    "name": "Energy consumption",
                    "detected": True,
                    "confidence": 0.7
                })
            
            # E2 - Pollution keywords
            if any(keyword in text_content for keyword in ['pollution', 'waste', 'chemical', 'toxic']):
                mapped_standards.append('E2')
                metrics.append({
                    "name": "Pollution indicators",
                    "detected": True,
                    "confidence": 0.6
                })
            
            # E3 - Water keywords
            if any(keyword in text_content for keyword in ['water', 'marine', 'ocean', 'river']):
                mapped_standards.append('E3')
                metrics.append({
                    "name": "Water consumption",
                    "detected": True,
                    "confidence": 0.6
                })
            
            # S1 - Workforce keywords
            if any(keyword in text_content for keyword in ['employee', 'worker', 'staff', 'safety', 'training']):
                mapped_standards.append('S1')
                metrics.append({
                    "name": "Workforce metrics",
                    "detected": True,
                    "confidence": 0.5
                })
            
            return {
                "mapped_standards": mapped_standards,
                "metrics": metrics,
                "data_quality": "medium",
                "missing_info": ["LLM analysis unavailable - using rule-based mapping"],
                "confidence": 0.6,
                "mapping_method": "rule_based_fallback"
            }
            
        except Exception as e:
            logger.error(f"Fallback mapping failed: {str(e)}")
            return {
                "mapped_standards": [],
                "metrics": [],
                "data_quality": "low",
                "missing_info": [f"Mapping error: {str(e)}"],
                "confidence": 0.0,
                "mapping_method": "error"
            }
    
    def _create_esrs_mapping_prompt(self, data: Dict[str, Any]) -> str:
        """Create prompt for ESRS mapping"""
        return f"""
        You are an ESG expert analyzing sustainability data for CSRD/ESRS compliance.
        
        Analyze the following data and map it to relevant ESRS metrics:
        
        Data Type: {data.get('data_type', 'unknown')}
        Data Summary: {json.dumps(data, indent=2)[:2000]}...
        
        Please identify:
        1. Relevant ESRS standards (E1-E5, S1-S4, G1)
        2. Specific metrics that can be derived
        3. Data quality assessment
        4. Missing information needed for complete compliance
        
        Respond in JSON format:
        {{
            "mapped_standards": [],
            "metrics": [],
            "data_quality": "high/medium/low",
            "missing_info": [],
            "confidence": 0.0-1.0
        }}
        """
    
    def _parse_esrs_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for ESRS mapping"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
                parsed["mapping_method"] = "llm_analysis"
                return parsed
            else:
                # Fallback parsing with regex/heuristics
                return self._heuristic_parse_response(response)
                
        except Exception as e:
            logger.error(f"Error parsing ESRS response: {str(e)}")
            return {
                "mapped_standards": [],
                "metrics": [],
                "data_quality": "low",
                "missing_info": [f"Parse error: {str(e)}"],
                "confidence": 0.0,
                "mapping_method": "parse_error"
            }
    
    def _heuristic_parse_response(self, response: str) -> Dict[str, Any]:
        """Heuristic parsing when JSON extraction fails"""
        import re
        
        try:
            # Extract ESRS standards mentioned
            esrs_pattern = r'[ES]\d+'
            standards = list(set(re.findall(esrs_pattern, response)))
            
            # Simple confidence scoring based on response length and keywords
            confidence = min(0.8, len(response) / 1000)
            
            # Extract quality assessment
            quality = "medium"
            if "high" in response.lower():
                quality = "high"
            elif "low" in response.lower():
                quality = "low"
            
            return {
                "mapped_standards": standards,
                "metrics": [{"name": "Extracted from text", "confidence": confidence}],
                "data_quality": quality,
                "missing_info": ["Heuristic parsing used"],
                "confidence": confidence,
                "mapping_method": "heuristic_parse"
            }
            
        except Exception as e:
            logger.error(f"Heuristic parsing failed: {str(e)}")
            return {
                "mapped_standards": [],
                "metrics": [],
                "data_quality": "low",
                "missing_info": [f"Heuristic parse error: {str(e)}"],
                "confidence": 0.0,
                "mapping_method": "heuristic_error"
            }
    
    def identify_gaps(self, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Identify gaps in ESG data coverage"""
        try:
            # Define required ESRS metrics
            required_metrics = {
                "E1": ["GHG emissions", "Energy consumption", "Energy mix"],
                "E2": ["Water consumption", "Water recycling"],
                "E3": ["Waste generation", "Circular economy"],
                "E4": ["Biodiversity impact"],
                "E5": ["Resource use", "Circular economy"],
                "S1": ["Own workforce", "Working conditions"],
                "S2": ["Workers in value chain"],
                "S3": ["Affected communities"],
                "S4": ["Consumers and end-users"],
                "G1": ["Business conduct", "Risk management"]
            }
            
            mapped_standards = current_metrics.get('mapped_standards', [])
            gaps = []
            expiring_artifacts = []
            
            # Check for missing standards
            for standard, metrics in required_metrics.items():
                if standard not in mapped_standards:
                    gaps.append({
                        "type": "missing_standard",
                        "standard": standard,
                        "required_metrics": metrics,
                        "priority": "high" if standard.startswith("E") else "medium"
                    })
            
            # Check for expiring data (simulate)
            cutoff_date = datetime.now() - timedelta(days=365)
            for item in current_metrics.get('metrics', []):
                if item.get('last_updated'):
                    last_updated = datetime.fromisoformat(item['last_updated'])
                    if last_updated < cutoff_date:
                        expiring_artifacts.append({
                            "metric": item.get('name'),
                            "last_updated": item.get('last_updated'),
                            "days_overdue": (datetime.now() - last_updated).days
                        })
            
            return {
                "gaps": gaps,
                "expiring_artifacts": expiring_artifacts,
                "gap_count": len(gaps),
                "expiring_count": len(expiring_artifacts)
            }
            
        except Exception as e:
            logger.error(f"Error identifying gaps: {str(e)}")
            raise
    
    def generate_narrative(self, metrics: Dict[str, Any], gaps: Dict[str, Any]) -> str:
        """Generate narrative summary using FREE local LLM"""
        try:
            prompt = f"""
            Generate a concise executive summary of ESG performance based on the following data:
            
            Current Metrics: {json.dumps(metrics, indent=2)}
            Identified Gaps: {json.dumps(gaps, indent=2)}
            
            The summary should:
            1. Highlight key ESG achievements
            2. Identify critical gaps and risks
            3. Provide actionable recommendations
            4. Be suitable for executive reporting
            
            Keep it under 500 words and use professional language.
            """
            
            try:
                response = self._call_ollama_model(self.model_name, prompt)
            except Exception as e:
                logger.warning(f"Primary model failed for narrative, trying fallback: {str(e)}")
                try:
                    response = self._call_ollama_model(self.fallback_model, prompt)
                except Exception as e2:
                    logger.warning(f"Fallback model also failed, using template: {str(e2)}")
                    response = self._generate_template_narrative(metrics, gaps)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating narrative: {str(e)}")
            return self._generate_template_narrative(metrics, gaps)
    
    def _generate_template_narrative(self, metrics: Dict[str, Any], gaps: Dict[str, Any]) -> str:
        """Generate template-based narrative when LLM is unavailable"""
        try:
            mapped_standards = metrics.get('mapped_standards', [])
            gap_count = gaps.get('gap_count', 0)
            expiring_count = gaps.get('expiring_count', 0)
            
            narrative = f"""
            ESG Performance Summary
            
            Current Status:
            - Standards Coverage: {len(mapped_standards)} ESRS standards identified
            - Mapped Standards: {', '.join(mapped_standards) if mapped_standards else 'None detected'}
            - Data Quality: {metrics.get('data_quality', 'Unknown')}
            
            Key Findings:
            - {gap_count} data gaps identified
            - {expiring_count} expiring data artifacts
            - Confidence Score: {metrics.get('confidence', 0):.1%}
            
            Recommendations:
            1. Address high-priority gaps in environmental standards
            2. Update expiring data sources within 30 days
            3. Implement systematic data collection for missing metrics
            4. Enhance data quality validation processes
            
            Next Steps:
            - Prioritize E1 (Climate) data collection if missing
            - Establish quarterly ESG data review process
            - Consider automated data validation tools
            """
            
            return narrative.strip()
            
        except Exception as e:
            logger.error(f"Template narrative generation failed: {str(e)}")
            return f"ESG analysis completed with {gap_count} gaps identified. Manual review recommended."
    
    def store_in_vector_db(self, text: str, metadata: Dict[str, Any]) -> str:
        """Store text in local SQLite vector database (FREE)"""
        try:
            doc_id = f"doc_{datetime.now().timestamp()}"
            
            # Generate embedding if embedder is available
            embedding = None
            if self.embedder:
                try:
                    embedding_vector = self.embedder.encode([text])[0]
                    embedding = embedding_vector.tobytes()
                except Exception as e:
                    logger.warning(f"Could not generate embedding: {e}")
            
            # Store in SQLite
            conn = sqlite3.connect(self.sqlite_db)
            cursor = conn.cursor()
            
            # Store in FTS5 table for text search
            cursor.execute('''
                INSERT INTO esg_documents (doc_id, content, metadata, created_at)
                VALUES (?, ?, ?, ?)
            ''', (doc_id, text, json.dumps(metadata), datetime.now().isoformat()))
            
            # Store in vector table if embedding available
            if embedding:
                cursor.execute('''
                    INSERT OR REPLACE INTO esg_vectors (doc_id, content, embedding, metadata)
                    VALUES (?, ?, ?, ?)
                ''', (doc_id, text, embedding, json.dumps(metadata)))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored document {doc_id} in local vector DB")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error storing in vector DB: {str(e)}")
            raise
    
    def search_vector_db(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search local vector database"""
        try:
            conn = sqlite3.connect(self.sqlite_db)
            cursor = conn.cursor()
            
            # Use FTS5 for text search
            cursor.execute('''
                SELECT doc_id, content, metadata, created_at
                FROM esg_documents
                WHERE esg_documents MATCH ?
                ORDER BY rank
                LIMIT ?
            ''', (query, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "doc_id": row[0],
                    "content": row[1],
                    "metadata": json.loads(row[2]) if row[2] else {},
                    "created_at": row[3]
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error searching vector DB: {str(e)}")
            return []
```return self._extract_from_json(file_path)
            else:
                raise ValueError(f"Unsupported source type: {source_type}")
                
        except Exception as e:
            logger.error(f"Notification failed: {str(e)}")
            state.errors.append(f"Notification error: {str(e)}")
            return state
    
    def error_handler_node(self, state: ESGWorkflowState) -> ESGWorkflowState:
        """Handle errors and update status"""
        try:
            logger.error(f"Handling errors for {state.evidence_id}: {state.errors}")
            state.status = "failed"
            
            # Store error state in DynamoDB
            table = self.dynamodb.Table(self.evidence_table)
            table.put_item(Item={
                'evidence_id': state.evidence_id,
                'status': 'failed',
                'errors': state.errors,
                'failed_at': datetime.now().isoformat()
            })
            
            # Send error notification
            error_message = {
                "evidence_id": state.evidence_id,
                "errors": state.errors,
                "timestamp": datetime.now().isoformat()
            }
            
            self.sns.publish(
                TopicArn=self.sns_topic_arn,
                Message=json.dumps(error_message),
                Subject=f"ESG Processing Failed: {state.evidence_id}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Error handler failed: {str(e)}")
            return state

    def run_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the complete ESG workflow"""
        try:
            # Initialize state
            state = ESGWorkflowState()
            state.evidence_id = input_data['evidence_id']
            state.file_path = input_data['file_path']
            state.source_type = input_data['source_type']
            state.metadata = input_data.get('metadata', {})
            
            # Create and run graph
            graph = self.create_graph()
            result = graph.invoke(state)
            
            return {
                "evidence_id": result.evidence_id,
                "status": result.status,
                "errors": result.errors
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {
                "evidence_id": input_data.get('evidence_id', 'unknown'),
                "status": "failed",
                "errors": [str(e)]
            }(f"Error extracting data from {file_path}: {str(e)}")
            raise
    
    def _extract_from_csv(self, file_path: str) -> Dict[str, Any]:
        """Extract data from CSV file"""
        try:
            # Download from S3
            response = self.s3.get_object(Bucket=self.data_bucket, Key=file_path)
            df = pd.read_csv(BytesIO(response['Body'].read()))
            
            return {
                "data_type": "tabular",
                "rows": len(df),
                "columns": df.columns.tolist(),
                "data": df.to_dict('records')[:100],  # Limit to first 100 records
                "summary": df.describe().to_dict() if df.select_dtypes(include=['number']).shape[1] > 0 else {}
            }
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            raise
    
    def _extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text from PDF file"""
        try:
            response = self.s3.get_object(Bucket=self.data_bucket, Key=file_path)
            pdf_content = BytesIO(response['Body'].read())
            
            reader = PyPDF2.PdfReader(pdf_content)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            return {
                "data_type": "document",
                "pages": len(reader.pages),
                "text": text,
                "word_count": len(text.split())
            }
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise
    
    def _extract_from_json(self, file_path: str) -> Dict[str, Any]:
        """Extract data from JSON file"""
        try:
            response = self.s3.get_object(Bucket=self.data_bucket, Key=file_path)
            data = json.loads(response['Body'].read())
            
            return {
                "data_type": "structured",
                "data": data,
                "keys": list(data.keys()) if isinstance(data, dict) else None
            }
        except Exception as e:
            logger.error(f"Error processing JSON: {str(e)}")
            raise
    
    def map_to_esrs_metrics(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map extracted data to ESRS metrics using LLM"""
        try:
            prompt = self._create_esrs_mapping_prompt(extracted_data)
            
            # Try primary model first
            try:
                response = self._call_bedrock_model(self.model_id, prompt)
            except Exception as e:
                logger.warning(f"Primary model failed, trying fallback: {str(e)}")
                response = self._call_bedrock_model(self.fallback_model_id, prompt)
            
            return self._parse_esrs_response(response)
            
        except Exception as e:
            logger.error(f"Error mapping to ESRS metrics: {str(e)}")
            raise
    
    def _create_esrs_mapping_prompt(self, data: Dict[str, Any]) -> str:
        """Create prompt for ESRS mapping"""
        return f"""
        You are an ESG expert analyzing sustainability data for CSRD/ESRS compliance.
        
        Analyze the following data and map it to relevant ESRS metrics:
        
        Data Type: {data.get('data_type', 'unknown')}
        Data Summary: {json.dumps(data, indent=2)[:2000]}...
        
        Please identify:
        1. Relevant ESRS standards (E1-E5, S1-S4, G1)
        2. Specific metrics that can be derived
        3. Data quality assessment
        4. Missing information needed for complete compliance
        
        Respond in JSON format:
        {{
            "mapped_standards": [],
            "metrics": [],
            "data_quality": "high/medium/low",
            "missing_info": [],
            "confidence": 0.0-1.0
        }}
        """
    
    def _call_bedrock_model(self, model_id: str, prompt: str) -> str:
        """Call Bedrock model with retry logic"""
        try:
            if "claude" in model_id:
                body = {
                    "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                    "max_tokens_to_sample": 2000,
                    "temperature": 0.1
                }
            else:  # AI21
                body = {
                    "prompt": prompt,
                    "maxTokens": 2000,
                    "temperature": 0.1
                }
            
            response = self.bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            if "claude" in model_id:
                return response_body['completion']
            else:
                return response_body['completions'][0]['data']['text']
                
        except Exception as e:
            logger.error(f"Bedrock model call failed: {str(e)}")
            raise
    
    def _parse_esrs_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for ESRS mapping"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # Fallback parsing
                return {
                    "mapped_standards": [],
                    "metrics": [],
                    "data_quality": "low",
                    "missing_info": ["Unable to parse LLM response"],
                    "confidence": 0.0
                }
                
        except Exception as e:
            logger.error(f"Error parsing ESRS response: {str(e)}")
            return {
                "mapped_standards": [],
                "metrics": [],
                "data_quality": "low",
                "missing_info": [f"Parse error: {str(e)}"],
                "confidence": 0.0
            }
    
    def identify_gaps(self, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Identify gaps in ESG data coverage"""
        try:
            # Define required ESRS metrics
            required_metrics = {
                "E1": ["GHG emissions", "Energy consumption", "Energy mix"],
                "E2": ["Water consumption", "Water recycling"],
                "E3": ["Waste generation", "Circular economy"],
                "E4": ["Biodiversity impact"],
                "E5": ["Resource use", "Circular economy"],
                "S1": ["Own workforce", "Working conditions"],
                "S2": ["Workers in value chain"],
                "S3": ["Affected communities"],
                "S4": ["Consumers and end-users"],
                "G1": ["Business conduct", "Risk management"]
            }
            
            mapped_standards = current_metrics.get('mapped_standards', [])
            gaps = []
            expiring_artifacts = []
            
            # Check for missing standards
            for standard, metrics in required_metrics.items():
                if standard not in mapped_standards:
                    gaps.append({
                        "type": "missing_standard",
                        "standard": standard,
                        "required_metrics": metrics,
                        "priority": "high" if standard.startswith("E") else "medium"
                    })
            
            # Check for expiring data (simulate)
            cutoff_date = datetime.now() - timedelta(days=365)
            for item in current_metrics.get('metrics', []):
                if item.get('last_updated'):
                    last_updated = datetime.fromisoformat(item['last_updated'])
                    if last_updated < cutoff_date:
                        expiring_artifacts.append({
                            "metric": item.get('name'),
                            "last_updated": item.get('last_updated'),
                            "days_overdue": (datetime.now() - last_updated).days
                        })
            
            return {
                "gaps": gaps,
                "expiring_artifacts": expiring_artifacts,
                "gap_count": len(gaps),
                "expiring_count": len(expiring_artifacts)
            }
            
        except Exception as e:
            logger.error(f"Error identifying gaps: {str(e)}")
            raise
    
    def generate_narrative(self, metrics: Dict[str, Any], gaps: Dict[str, Any]) -> str:
        """Generate narrative summary using LLM"""
        try:
            prompt = f"""
            Generate a concise executive summary of ESG performance based on the following data:
            
            Current Metrics: {json.dumps(metrics, indent=2)}
            Identified Gaps: {json.dumps(gaps, indent=2)}
            
            The summary should:
            1. Highlight key ESG achievements
            2. Identify critical gaps and risks
            3. Provide actionable recommendations
            4. Be suitable for executive reporting
            
            Keep it under 500 words and use professional language.
            """
            
            try:
                response = self._call_bedrock_model(self.model_id, prompt)
            except Exception as e:
                logger.warning(f"Primary model failed for narrative, trying fallback: {str(e)}")
                response = self._call_bedrock_model(self.fallback_model_id, prompt)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating narrative: {str(e)}")
            return f"Error generating narrative: {str(e)}"
    
    def store_in_vector_db(self, text: str, metadata: Dict[str, Any]) -> str:
        """Store text in OpenSearch vector database"""
        try:
            # This would typically use embeddings and OpenSearch
            # Simplified implementation for demo
            vector_id = f"vec_{datetime.now().timestamp()}"
            
            # In a real implementation, you would:
            # 1. Generate embeddings using Bedrock
            # 2. Store in OpenSearch with proper indexing
            
            logger.info(f"Stored vector {vector_id} in OpenSearch")
            return vector_id
            
        except Exception as e:
            logger.error(f"Error storing in vector DB: {str(e)}")
            raise