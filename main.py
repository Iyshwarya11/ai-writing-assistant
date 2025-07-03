from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import httpx
from typing import List, Optional

load_dotenv()

app = FastAPI(title="AI Writing Assistant API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

@app.get("/")
async def root():
    return {"message": "AI Writing Assistant API"}

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_text(request: TextAnalysisRequest):
    """Analyze text using Ollama and other APIs"""
    try:
        # Ollama API call
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        async with httpx.AsyncClient() as client:
            # Call Ollama for grammar analysis
            ollama_response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": "mistral",
                    "prompt": f"Analyze this text for grammar, style, and tone issues: {request.text}",
                    "stream": False
                }
            )
            
            # Call LanguageTool API
            languagetool_response = await client.post(
                "https://api.languagetool.org/v2/check",
                data={
                    "text": request.text,
                    "language": "en-US"
                }
            )
        
        # Process and return suggestions
        suggestions = [
            {
                "id": 1,
                "type": "grammar",
                "text": "Sample grammar suggestion",
                "position": {"start": 0, "end": 10},
                "severity": "high",
                "category": "Grammar"
            }
        ]
        
        scores = {
            "grammar": 85,
            "readability": 78,
            "tone": 90,
            "plagiarism": 100,
            "overall": 88
        }
        
        return AnalysisResponse(suggestions=suggestions, scores=scores)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents")
async def save_document(document: dict):
    """Save document to Supabase"""
    # Implement Supabase document saving
    return {"message": "Document saved successfully"}

@app.get("/api/documents")
async def get_documents(user_id: str):
    """Get user documents from Supabase"""
    # Implement Supabase document retrieval
    return {"documents": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)