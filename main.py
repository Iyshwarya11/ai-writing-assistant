from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Writing Assistant API",
    description="Free AI-powered writing assistant with grammar checking and analysis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "https://*.vercel.app",
        "https://*.netlify.app",
        "https://*.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class TextAnalysisRequest(BaseModel):
    text: str
    user_id: Optional[str] = None

class Suggestion(BaseModel):
    id: int
    type: str
    text: str
    position: dict
    severity: str
    category: str

class AnalysisResponse(BaseModel):
    suggestions: List[Suggestion]
    scores: dict

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "AI Writing Assistant API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024"}

# Main analysis endpoint
@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_text(request: TextAnalysisRequest):
    """Analyze text using free LanguageTool API"""
    try:
        suggestions = []
        suggestion_id = 1
        
        # Basic validation
        if not request.text or len(request.text.strip()) == 0:
            return AnalysisResponse(
                suggestions=[],
                scores={
                    "grammar": 0,
                    "readability": 0,
                    "tone": 0,
                    "plagiarism": 0,
                    "overall": 0
                }
            )
        
        # Free LanguageTool API call
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.languagetool.org/v2/check",
                    data={
                        "text": request.text,
                        "language": "en-US",
                        "enabledOnly": "false"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Process LanguageTool matches
                    for match in data.get("matches", []):
                        rule = match.get("rule", {})
                        category = rule.get("category", {})
                        
                        # Determine severity based on rule category
                        severity = "medium"
                        if category.get("id") == "TYPOS":
                            severity = "high"
                        elif category.get("id") == "GRAMMAR":
                            severity = "high"
                        elif category.get("id") == "STYLE":
                            severity = "low"
                        
                        suggestions.append({
                            "id": suggestion_id,
                            "type": "grammar",
                            "text": match.get("message", "Grammar issue found"),
                            "position": {
                                "start": match.get("offset", 0),
                                "end": match.get("offset", 0) + match.get("length", 0)
                            },
                            "severity": severity,
                            "category": category.get("name", "Grammar")
                        })
                        suggestion_id += 1
                else:
                    logger.warning(f"LanguageTool API returned status {response.status_code}")
                    
        except Exception as e:
            logger.error(f"LanguageTool API error: {e}")
            # Add a fallback suggestion if API fails
            suggestions.append({
                "id": suggestion_id,
                "type": "info",
                "text": "Grammar check temporarily unavailable",
                "position": {"start": 0, "end": 0},
                "severity": "low",
                "category": "System"
            })
        
        # Basic readability analysis
        readability_suggestions = analyze_readability(request.text, suggestion_id)
        suggestions.extend(readability_suggestions)
        
        # Calculate scores
        scores = calculate_scores(request.text, suggestions)
        
        logger.info(f"Analysis complete: {len(suggestions)} suggestions, overall score: {scores['overall']}")
        
        return AnalysisResponse(suggestions=suggestions, scores=scores)
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

def analyze_readability(text: str, start_id: int) -> List[dict]:
    """Analyze text readability and return suggestions"""
    suggestions = []
    current_id = start_id
    
    # Check sentence length
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    long_sentences = [s for s in sentences if len(s.split()) > 25]
    
    if long_sentences:
        suggestions.append({
            "id": current_id,
            "type": "readability",
            "text": f"Consider breaking long sentences into shorter ones for better readability",
            "position": {"start": 0, "end": len(text)},
            "severity": "medium",
            "category": "Readability"
        })
        current_id += 1
    
    # Check paragraph length
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    long_paragraphs = [p for p in paragraphs if len(p.split()) > 150]
    
    if long_paragraphs:
        suggestions.append({
            "id": current_id,
            "type": "readability",
            "text": "Consider breaking long paragraphs into smaller ones",
            "position": {"start": 0, "end": len(text)},
            "severity": "low",
            "category": "Readability"
        })
        current_id += 1
    
    return suggestions

def calculate_scores(text: str, suggestions: List[dict]) -> dict:
    """Calculate writing quality scores"""
    
    # Basic text metrics
    words = text.split()
    word_count = len(words)
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    sentence_count = len(sentences)
    
    # Grammar score (based on grammar suggestions)
    grammar_errors = len([s for s in suggestions if s["type"] == "grammar" and s["severity"] == "high"])
    grammar_score = max(60, 100 - (grammar_errors * 8))
    
    # Readability score (based on sentence complexity)
    if sentence_count > 0:
        avg_sentence_length = word_count / sentence_count
        if avg_sentence_length <= 15:
            readability = 95
        elif avg_sentence_length <= 20:
            readability = 85
        elif avg_sentence_length <= 25:
            readability = 75
        else:
            readability = 65
    else:
        readability = 50
    
    # Tone score (mock implementation - can be enhanced)
    tone_score = 85
    
    # Plagiarism score (mock - always high for demo)
    plagiarism_score = 95
    
    # Overall score
    overall = int((grammar_score + readability + tone_score + plagiarism_score) / 4)
    
    return {
        "grammar": int(grammar_score),
        "readability": int(readability),
        "tone": int(tone_score),
        "plagiarism": int(plagiarism_score),
        "overall": overall
    }

# Additional endpoints for future features
@app.post("/api/documents")
async def save_document(document: dict):
    """Save document endpoint - placeholder"""
    return {"message": "Document saved successfully", "id": "temp_id"}

@app.get("/api/documents")
async def get_documents(user_id: str):
    """Get documents endpoint - placeholder"""
    return {"documents": []}

# For Render deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)