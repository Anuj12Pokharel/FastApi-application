from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from pathlib import Path

# Explicitly load the .env file located next to this script so the running
# process reliably picks it up even if uvicorn is started from another cwd.
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Helpful debug print for local development to confirm the key is visible
import os
_gkey = os.getenv("GOOGLE_API_KEY")
_okey = os.getenv("OPENAI_API_KEY")
print("GOOGLE_API_KEY set:", bool(_gkey))
print("OPENAI_API_KEY set:", bool(_okey))

# Import rag_service after loading env so it can read GOOGLE_API_KEY at import-time
import rag_service

app = FastAPI(title="RAG Application")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the RAG API. Upload a document to start."}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("OPENAI_API_KEY"):
         raise HTTPException(status_code=500, detail="Neither GOOGLE_API_KEY nor OPENAI_API_KEY is set in server environment.")
    
    try:
        result = await rag_service.process_document(file)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat(request: QueryRequest):
    try:
        response = rag_service.ask_question(request.question)
        if "error" in response:
             raise HTTPException(status_code=400, detail=response["error"])
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
