"""
Streamlit Frontend for Contract RAG System
Allows PDF ingestion and querying through FastAPI backend
Backend auto-initializes from .env file
"""

import streamlit as st
import requests
from typing import List, Dict, Any
import time

st.set_page_config(
    page_title="Contract RAG System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = "http://localhost:8000"

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_stats' not in st.session_state:
    st.session_state.current_stats = {}

def upload_pdf(file) -> Dict[str, Any]:
    """Upload PDF to backend for ingestion"""
    try:
        files = {"file": (file.name, file, "application/pdf")}
        response = requests.post(f"{BACKEND_URL}/ingest", files=files)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def query_backend(query: str, num_results: int = 5) -> Dict[str, Any]:
    """Query the backend"""
    try:
        payload = {"query": query, "num_results": num_results}
        response = requests.post(f"{BACKEND_URL}/query", json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json().get('detail', 'Query failed')}
    except Exception as e:
        return {"error": str(e)}

def get_stats() -> Dict[str, Any]:
    """Get database statistics"""
    try:
        response = requests.get(f"{BACKEND_URL}/stats")
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error"}
    except:
        return {"status": "error"}

def clear_collection() -> bool:
    """Clear the collection"""
    try:
        response = requests.delete(f"{BACKEND_URL}/clear")
        return response.status_code == 200
    except:
        return False

with st.sidebar:
    st.title("🛠️ Contract RAG System")
    
    try:
        response = requests.get(f"{BACKEND_URL}/")
        backend_data = response.json()
        backend_connected = backend_data.get("status") in ["running", "not_initialized"]
        system_initialized = backend_data.get("initialized", False)
    except:
        backend_connected = False
        system_initialized = False
    
    if backend_connected and system_initialized:
        st.success("✅ System Ready")
    elif backend_connected:
        st.warning("⚠️ Backend Running (Not Initialized)")
        st.info("Check .env file for GROQ_API_KEY")
    else:
        st.error("❌ Backend Not Connected")
        st.info("Start backend: `python backend.py`")
    
    st.markdown("---")
    
    tab_selection = st.radio(
        "Select Operation",
        ["📤 Ingest PDFs", "🔍 Query Documents"],
        label_visibility="collapsed"
    )
    
    
    if system_initialized:
        
        if st.session_state.current_stats.get("status") == "success":
            details = st.session_state.current_stats.get("details", {})
            
            col1, col2 = st.columns(2)
            col1.metric("📄 Total Chunks", details.get("total_chunks", 0))
            col2.metric("📚 Unique PDFs", details.get("unique_pdfs", 0))
            
            if details.get("pdf_list"):
                with st.expander("📋 Ingested PDFs"):
                    for pdf in details.get("pdf_list", []):
                        st.text(f"• {pdf}")
        
        st.markdown("---")
        if st.button("🗑️ Clear Collection", type="secondary", use_container_width=True):
            if st.session_state.get('confirm_clear'):
                with st.spinner("Clearing..."):
                    if clear_collection():
                        st.success("Collection cleared!")
                        st.session_state.current_stats = {}
                        st.session_state.confirm_clear = False
                        time.sleep(1)
                        st.rerun()
            else:
                st.session_state.confirm_clear = True
                st.warning("⚠️ Click again to confirm deletion")

st.title("📄 Contract RAG System")

if not system_initialized:
    st.warning("⚠️ System not initialized. Please check backend logs and ensure GROQ_API_KEY is set in .env file!")
    st.info("Backend should auto-initialize on startup if .env is configured correctly.")
    
    st.markdown("### 🎯 What can this system do?")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📤 PDF Ingestion:**
        - Upload contract PDFs
        - Automatic text extraction
        - Intelligent chunking
        - Vector embedding storage
        """)
    
    with col2:
        st.markdown("""
        **🔍 Document Querying:**
        - Natural language questions
        - Semantic search
        - Source attribution
        - Similarity scoring
        """)

else:

    if tab_selection == "📤 Ingest PDFs":
        st.header("📤 Ingest PDF Documents")
        
        st.markdown("""
        Upload PDF contract documents to add them to the knowledge base.
        The system will extract text, create chunks, and store vector embeddings.
        """)
        
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload one or more PDF files to ingest"
        )
        
        if uploaded_files:
            if st.button("📥 Ingest All Files", type="primary"):
                progress_bar = st.progress(0)
                status_container = st.empty()
                
                results = []
                for i, uploaded_file in enumerate(uploaded_files):
                    status_container.info(f"Processing: {uploaded_file.name}")
                    
                    result = upload_pdf(uploaded_file)
                    results.append({
                        "filename": uploaded_file.name,
                        "status": result.get("status"),
                        "details": result.get("details", {}),
                        "message": result.get("message", "")
                    })
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_container.empty()
                progress_bar.empty()
                
                st.markdown("### 📊 Ingestion Results")
                
                success_count = sum(1 for r in results if r["status"] == "success")
                st.metric("Successfully Ingested", f"{success_count}/{len(results)}")
                
                for result in results:
                    if result["status"] == "success":
                        with st.expander(f"✅ {result['filename']}", expanded=False):
                            details = result.get("details", {})
                            col1, col2 = st.columns(2)
                            col1.metric("Chunks Created", details.get("chunks_created", "N/A"))
                            col2.metric("Text Length", f"{details.get('text_length', 0):,} chars")
                    else:
                        with st.expander(f"❌ {result['filename']}", expanded=True):
                            st.error(result.get("message", "Unknown error"))
                
             
                st.session_state.current_stats = get_stats()
    
    else:
        st.header("🔍 Query Documents")
        
        query = st.text_input(
            "Enter your question",
            placeholder="e.g., What are the termination clauses in these contracts?",
            help="Ask questions about the ingested contract documents"
        )
        
        with st.expander("⚙️ Query Options"):
            custom_num_results = st.slider(
                "Number of chunks to retrieve",
                min_value=3,
                max_value=15,
                value=5,
                help="More chunks provide more context but may include less relevant information"
            )
        
        st.markdown("**💡 Example Questions:**")
        example_cols = st.columns(3)
        example_questions = [
            "What are the key termination clauses?",
            "Summarize the payment terms",
            "What intellectual property clauses exist?"
        ]
        
        selected_example = None
        for i, example in enumerate(example_questions):
            with example_cols[i]:
                if st.button(example, key=f"example_{i}", use_container_width=True):
                    selected_example = example
        if selected_example:
            query = selected_example
        
        if st.button("🔍 Search", type="primary", disabled=not query):
            if query:
                with st.spinner("🤔 Analyzing documents..."):
                    response = query_backend(query, custom_num_results)
                    
                    if "error" in response:
                        st.error(f"❌ Query failed: {response['error']}")
                    else:
                        st.session_state.chat_history.append({
                            "question": query,
                            "answer": response["answer"],
                            "sources": response["sources"]
                        })
                        
                    
                        st.markdown("### 💬 Answer")
                        st.markdown(response["answer"])
                        
                        st.markdown("### 📚 Source Documents")
                        st.markdown("*Retrieved chunks ranked by relevance with similarity scores*")
                        
                        for source in response["sources"]:
                            similarity_pct = source["similarity_score"] * 100
                            
                            if similarity_pct >= 70:
                                color = "🟢"
                            elif similarity_pct >= 50:
                                color = "🟡"
                            else:
                                color = "🔴"
                            
                            with st.expander(
                                f"{color} Rank #{source['rank']} | {source['source_file']} | "
                                f"Chunk {source['chunk_id']}/{source['total_chunks']} | "
                                f"Similarity: {similarity_pct:.1f}%",
                                expanded=(source['rank'] == 1)
                            ):
                                st.progress(source["similarity_score"])
                                
                                # Metadata
                                col1, col2, col3, col4 = st.columns(4)
                                col1.metric("Rank", source['rank'])
                                col2.metric("Chunk", f"{source['chunk_id']}/{source['total_chunks']}")
                                col3.metric("Similarity", f"{similarity_pct:.1f}%")
                                col4.metric("File", source['source_file'][:20] + "...")
                                
                                st.markdown("**Content:**")
                                st.text_area(
                                    "Chunk Content",
                                    value=source['content'],
                                    height=200,
                                    key=f"source_{source['rank']}",
                                    label_visibility="collapsed"
                                )
        
    
        if st.session_state.chat_history:
            st.markdown("---")
            st.markdown("### 📜 Recent Queries")
            
            
            for i, chat in enumerate(reversed(st.session_state.chat_history[-5:])):
                with st.expander(
                    f"Q: {chat['question'][:80]}{'...' if len(chat['question']) > 80 else ''}",
                    expanded=False
                ):
                    st.markdown(f"**Question:** {chat['question']}")
                    st.markdown(f"**Answer:** {chat['answer'][:300]}{'...' if len(chat['answer']) > 300 else ''}")
                    st.caption(f"📊 {len(chat['sources'])} source documents retrieved")
            
            
            if st.button("🗑️ Clear History"):
                st.session_state.chat_history = []
                st.rerun()

st.markdown("---")
st.caption("🚀 Powered by FastAPI + Streamlit | 🦙 Groq LLaMA | 🤗 HuggingFace | 🐘 PostgreSQL + pgvector")
