import os
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException
from pypdf import PdfReader
from app.services.vector_store import NIDAVectorStore

router = APIRouter()

@router.post("/api/admin/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        # Create temp dir
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Read PDF
        reader = PdfReader(file_path)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text() + "\n"
            
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
            
        # Upsert to Pinecone
        vs = NIDAVectorStore.get_instance()
        vs.upsert_pdf_document(text_content, file.filename)
        
        # Cleanup
        os.remove(file_path)
        
        return {"status": "success", "message": f"Successfully ingested {file.filename} into knowledge base."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
