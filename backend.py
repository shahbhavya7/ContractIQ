"""
FastAPI Backend for Contract RAG System
Handles PDF ingestion, chunking, vector storage, and retrieval
Auto-initializes on startup with environment variables
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import tempfile
from pathlib import Path
import shutil
import uuid
import time
from dotenv import load_dotenv

load_dotenv()

from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document

from pdfminer.high_level import extract_text
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Text
import psycopg

from testset_generator import ContractTestsetGenerator

app = FastAPI(title="Contract RAG Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


EMBEDDINGS = None
VECTOR_STORE = None
QA_CHAIN = None
LLM = None


DB_CONFIG = {
    "db_host": os.getenv("DB_HOST", "localhost"),
    "db_port": os.getenv("DB_PORT", "5432"),
    "db_user": os.getenv("DB_USER", "vect"),
    "db_password": os.getenv("DB_PASSWORD", "vect"),
    "db_name": os.getenv("DB_NAME", "vect"),
    "collection_name": os.getenv("COLLECTION_NAME", "contract_rag_collection"),
    "groq_api_key": os.getenv("GROQ_API_KEY"),
    "llm_model": os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
    "temperature": float(os.getenv("TEMPERATURE", "0.0")),
    "num_results": int(os.getenv("NUM_RESULTS", "5"))
}


class QueryRequest(BaseModel):
    query: str
    num_results: Optional[int] = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

class StatusResponse(BaseModel):
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None

class TestsetGenerationRequest(BaseModel):
    testset_size: int = 10
    save_to_disk: bool = True

class TestsetGenerationResponse(BaseModel):
    status: str
    message: str
    testset: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pdfminer (fast extraction)"""
    try:
        text = extract_text(pdf_path)
        return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def chunk_text(text: str, source_file: str, max_chars: int = 800) -> List[Document]:
    """Chunk text using unstructured's chunk_by_title (preserves document structure)"""
    try:
        
        elements = [Text(text=text)]
        
        
        chunks = chunk_by_title(
            elements,
            max_characters=max_chars,
            new_after_n_chars=int(max_chars * 0.8),
            combine_text_under_n_chars=100  # Combine small sections
        )
        
        
        documents = []
        for i, chunk in enumerate(chunks, 1):
            doc = Document(
                page_content=chunk.text,
                metadata={
                    "source_file": source_file,
                    "chunk_id": i,
                    "total_chunks": len(chunks),
                    "chunk_type": "title_based"
                }
            )
            documents.append(doc)
        
        return documents
    except Exception as e:
        raise Exception(f"Error chunking text: {str(e)}")

def get_embeddings():
    """Get or create embeddings model (cached in memory)"""
    global EMBEDDINGS
    if EMBEDDINGS is None:
        print("   Loading embeddings model (first time only)...")
        EMBEDDINGS = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True},
            show_progress=False  
        )
    return EMBEDDINGS

def get_connection_string():
    """Build PostgreSQL connection string"""
    return f"postgresql+psycopg://{DB_CONFIG['db_user']}:{DB_CONFIG['db_password']}@{DB_CONFIG['db_host']}:{DB_CONFIG['db_port']}/{DB_CONFIG['db_name']}"

def initialize_system():
    """Initialize the RAG system with embeddings and LLM on startup (OPTIMIZED)"""
    global EMBEDDINGS, VECTOR_STORE, QA_CHAIN, LLM
    
    try:
        start_time = time.time()
        
        
        if not DB_CONFIG.get("groq_api_key"):
            raise Exception("GROQ_API_KEY not found in environment variables. Please set it in .env file")
        
        
        os.environ["GROQ_API_KEY"] = DB_CONFIG["groq_api_key"]
        
       
        print(" Loading embeddings model...")
        embed_start = time.time()
        EMBEDDINGS = get_embeddings()
        print(f" Loaded in {time.time() - embed_start:.2f}s")
        
        
        print("Setting up PostgreSQL connection...")
        db_start = time.time()
        connection = get_connection_string()
        
    
        VECTOR_STORE = PGVector(
            embeddings=EMBEDDINGS,
            collection_name=DB_CONFIG["collection_name"],
            connection=connection,
            use_jsonb=True,
            pre_delete_collection=False, 
        )
        print(f"Connected in {time.time() - db_start:.2f}s")
        
    
        print(f"Initializing LLM client...")
        llm_start = time.time()
        LLM = ChatGroq(
            model=DB_CONFIG["llm_model"],
            temperature=DB_CONFIG["temperature"],
            api_key=DB_CONFIG["groq_api_key"],
            max_retries=2,  
        )
        print(f"Ready in {time.time() - llm_start:.2f}s")
        
        
        retriever = VECTOR_STORE.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": DB_CONFIG["num_results"],
                "fetch_k": DB_CONFIG["num_results"] * 2  
            }
        )
        
       
        prompt_template = """You are a helpful AI assistant specialized in analyzing contract documents. 
Use the following pieces of context from contract documents to answer the question at the end.
If you don't know the answer based on the context, just say that you don't know, don't make up an answer.
Provide detailed, well-structured answers with relevant citations from the contracts when applicable.

Context:
{context}

Question: {question}

Detailed Answer:"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        
        print(" Building RAG chain...")
        QA_CHAIN = RetrievalQA.from_chain_type(
            llm=LLM,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": PROMPT},
            return_source_documents=True
        )
        
        total_time = time.time() - start_time
        print(f"\n System ready in {total_time:.2f}s!")
        print(f"Collection: {DB_CONFIG['collection_name']}")
        print(f"LLM: {DB_CONFIG['llm_model']}")
        print(f"Database: {DB_CONFIG['db_host']}:{DB_CONFIG['db_port']}/{DB_CONFIG['db_name']}")
        
    except Exception as e:
        print(f"Initialization failed: {str(e)}")
        raise


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    print("\n" + "="*60)
    print("Starting Contract RAG Backend")
    print("="*60)
    initialize_system()
    print("="*60 + "\n")

# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running" if QA_CHAIN is not None else "not_initialized",
        "service": "Contract RAG Backend",
        "version": "1.0.0",
        "initialized": QA_CHAIN is not None
    }

@app.post("/ingest", response_model=StatusResponse)
async def ingest_pdf(file: UploadFile = File(...)):
    """Ingest a PDF file, chunk it, and store in vector database (OPTIMIZED FOR SPEED)"""
    global VECTOR_STORE, EMBEDDINGS
    
    if VECTOR_STORE is None or EMBEDDINGS is None:
        raise HTTPException(status_code=400, detail="System not initialized. Check backend logs and .env configuration.")
    
   
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    temp_file_path = None
    try:
        print(f"Processing: {file.filename}")
        start_time = time.time()
        
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        print(f" File saved: {time.time() - start_time:.2f}s")
        
        extract_start = time.time()
        text = extract_text_from_pdf(temp_file_path)
        print(f"Text extracted: {time.time() - extract_start:.2f}s")
        
        if not text or len(text.strip()) < 100:
            raise HTTPException(status_code=400, detail="PDF appears to be empty or contains insufficient text")
        
        chunk_start = time.time()
        documents = chunk_text(text, file.filename, max_chars=800)
        print(f"Text chunked: {time.time() - chunk_start:.2f}s ({len(documents)} chunks)")
        
        if not documents:
            raise HTTPException(status_code=400, detail="Failed to create chunks from PDF")
        
        embed_start = time.time()
        VECTOR_STORE.add_documents(documents)
        print(f"Embeddings stored: {time.time() - embed_start:.2f}s")
        
        total_time = time.time() - start_time
        print(f"Total time: {total_time:.2f}s")
        
        return StatusResponse(
            status="success",
            message=f"PDF ingested successfully in {total_time:.2f}s",
            details={
                "filename": file.filename,
                "chunks_created": len(documents),
                "text_length": len(text),
                "processing_time": f"{total_time:.2f}s"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
    
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query ALL documents in the database (previously embedded + newly uploaded)"""
    global QA_CHAIN, VECTOR_STORE
    
    if QA_CHAIN is None or VECTOR_STORE is None:
        raise HTTPException(status_code=400, detail="System not initialized. Check backend logs and .env configuration.")
    
    try:
        
        docs_with_scores = VECTOR_STORE.similarity_search_with_score(
            request.query,
            k=request.num_results
        )
        
        response = QA_CHAIN.invoke({"query": request.query})
        
        sources = []
        for i, (doc, score) in enumerate(docs_with_scores, 1):
            source = {
                "rank": i,
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": float(1 - score), 
                "source_file": doc.metadata.get("source_file", "Unknown"),
                "chunk_id": doc.metadata.get("chunk_id", "N/A"),
                "total_chunks": doc.metadata.get("total_chunks", "N/A")
            }
            sources.append(source)
        
        return QueryResponse(
            answer=response["result"],
            sources=sources
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/stats", response_model=StatusResponse)
async def get_database_stats():
    """Get statistics about the database"""
    if not DB_CONFIG or not DB_CONFIG.get("groq_api_key"):
        raise HTTPException(status_code=400, detail="System not initialized. Check backend logs and .env configuration.")
    
    try:
        conn_str = f"postgresql://{DB_CONFIG['db_user']}:{DB_CONFIG['db_password']}@{DB_CONFIG['db_host']}:{DB_CONFIG['db_port']}/{DB_CONFIG['db_name']}"
        
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                # Get collection UUID
                cur.execute("""
                    SELECT uuid FROM langchain_pg_collection 
                    WHERE name = %s
                """, (DB_CONFIG['collection_name'],))
                row = cur.fetchone()
                
                if not row:
                    return StatusResponse(
                        status="success",
                        message="Collection not found or empty",
                        details={
                            "total_chunks": 0,
                            "unique_pdfs": 0,
                            "collection_name": DB_CONFIG['collection_name']
                        }
                    )
                
                col_uuid = row[0]
                
                # Get stats
                cur.execute("""
                    SELECT 
                        COUNT(*) AS total_chunks,
                        COUNT(DISTINCT cmetadata->>'source_file') AS unique_pdfs
                    FROM langchain_pg_embedding
                    WHERE collection_id = %s
                """, (col_uuid,))
                total_chunks, unique_pdfs = cur.fetchone()
                
                # Get list of PDFs
                cur.execute("""
                    SELECT DISTINCT cmetadata->>'source_file' as pdf_name
                    FROM langchain_pg_embedding
                    WHERE collection_id = %s
                    ORDER BY pdf_name
                """, (col_uuid,))
                pdf_list = [row[0] for row in cur.fetchall()]
                
                return StatusResponse(
                    status="success",
                    message="Database statistics retrieved",
                    details={
                        "total_chunks": total_chunks,
                        "unique_pdfs": unique_pdfs,
                        "collection_name": DB_CONFIG['collection_name'],
                        "pdf_list": pdf_list
                    }
                )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.delete("/clear", response_model=StatusResponse)
async def clear_collection():
    """Clear all documents from the current collection"""
    global VECTOR_STORE
    
    if not DB_CONFIG or not DB_CONFIG.get("groq_api_key"):
        raise HTTPException(status_code=400, detail="System not initialized. Check backend logs and .env configuration.")
    
    try:
        conn_str = f"postgresql://{DB_CONFIG['db_user']}:{DB_CONFIG['db_password']}@{DB_CONFIG['db_host']}:{DB_CONFIG['db_port']}/{DB_CONFIG['db_name']}"
        
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                # Get collection UUID
                cur.execute("""
                    SELECT uuid FROM langchain_pg_collection 
                    WHERE name = %s
                """, (DB_CONFIG['collection_name'],))
                row = cur.fetchone()
                
                if row:
                    col_uuid = row[0]
                    # Delete all embeddings
                    cur.execute("""
                        DELETE FROM langchain_pg_embedding
                        WHERE collection_id = %s
                    """, (col_uuid,))
                    conn.commit()
                    
                    return StatusResponse(
                        status="success",
                        message="Collection cleared successfully",
                        details={"collection_name": DB_CONFIG['collection_name']}
                    )
                else:
                    return StatusResponse(
                        status="success",
                        message="Collection not found or already empty"
                    )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear collection: {str(e)}")

@app.post("/generate-testset", response_model=TestsetGenerationResponse)
async def generate_testset(request: TestsetGenerationRequest):
    """
    Generate a Ragas testset from all documents in the vector store
    Uses Groq for LLM and HuggingFace for embeddings (same as main RAG system)
    """
    global VECTOR_STORE
    
    if VECTOR_STORE is None:
        raise HTTPException(status_code=400, detail="System not initialized. Check backend logs.")
    
    if not DB_CONFIG.get("groq_api_key"):
        raise HTTPException(
            status_code=400,
            detail="GROQ_API_KEY not found. Please add it to your .env file."
        )
    
    try:
        print(f"\n{'='*60}")
        print(f"Starting Testset Generation")
        print(f"{'='*60}")
        
        # Initialize testset generator (only needs Groq API key)
        generator = ContractTestsetGenerator(
            groq_api_key=DB_CONFIG["groq_api_key"],
            llm_model=DB_CONFIG["llm_model"]
        )
        
        # Setup save directory
        save_dir = "testsets" if request.save_to_disk else None
        
        # Generate testset from vector store (with fast mode enabled by default)
        result = generator.generate_from_vector_store(
            vector_store=VECTOR_STORE,
            collection_name=DB_CONFIG["collection_name"],
            testset_size=request.testset_size,
            save_dir=save_dir,
            fast_mode=True  # Enable for 5-10x speedup
        )
        
        # Convert DataFrame to list of dicts for JSON response
        testset_list = result["testset"].to_dict(orient="records")
        
        print(f"{'='*60}")
        print(f"✓ Testset Generation Complete!")
        print(f"{'='*60}\n")
        
        return TestsetGenerationResponse(
            status="success",
            message=f"Successfully generated {len(testset_list)} test questions",
            testset=testset_list,
            metadata=result["metadata"]
        )
    
    except Exception as e:
        print(f"Testset generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Testset generation failed: {str(e)}")

@app.get("/testset-files")
async def list_testset_files():
    """List all generated testset files"""
    testsets_dir = "testsets"
    
    if not os.path.exists(testsets_dir):
        return {"status": "success", "files": []}
    
    try:
        files = []
        for filename in os.listdir(testsets_dir):
            if filename.endswith(".csv"):
                filepath = os.path.join(testsets_dir, filename)
                file_info = {
                    "filename": filename,
                    "path": filepath,
                    "size": os.path.getsize(filepath),
                    "modified": os.path.getmtime(filepath)
                }
                files.append(file_info)
        
        # Sort by modified time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"status": "success", "files": files}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list testset files: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
