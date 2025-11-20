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

def generate_testset(testset_size: int = 10, save_to_disk: bool = True, source_file: str = None) -> Dict[str, Any]:
    """Generate a testset using Ragas"""
    try:
        payload = {
            "testset_size": testset_size,
            "save_to_disk": save_to_disk,
            "source_file": source_file
        }
        response = requests.post(f"{BACKEND_URL}/generate-testset", json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": response.json().get('detail', 'Generation failed')}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_testset_files() -> List[Dict[str, Any]]:
    """Get list of generated testset files"""
    try:
        response = requests.get(f"{BACKEND_URL}/testset-files")
        if response.status_code == 200:
            return response.json().get("files", [])
        return []
    except:
        return []

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
        ["📤 Ingest PDFs", "🔍 Query Documents", "🧪 Generate Testset"],
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
    
    elif tab_selection == "🧪 Generate Testset":
        st.header("🧪 Generate Evaluation Testset")
        
        # Get list of available PDFs - refresh on each load
        stats = get_stats()
        available_pdfs = []
        if stats.get("status") == "success" and stats.get("details"):
            available_pdfs = stats["details"].get("pdf_list", [])
        
        if not available_pdfs:
            st.warning("⚠️ No PDFs found in the collection. Please ingest at least one PDF document first.")
            st.info("👉 Go to the **Ingest PDFs** tab to upload documents.")
            st.stop()
        
        # PDF Selection - Always visible when PDFs are available
        st.markdown("### 📄 Select Source Documents")
        st.success(f"✅ Found {len(available_pdfs)} PDF(s) in collection")
        
        generation_mode = st.radio(
            "Generation Mode:",
            ["📄 Single PDF (Faster, Recommended)", "🌐 All Documents"],
            help="Single PDF mode is much faster and uses fewer tokens",
            horizontal=True
        )
        
        selected_pdf = None
        
        if generation_mode == "📄 Single PDF (Faster, Recommended)":
            st.markdown("#### Choose a specific PDF:")
            selected_pdf = st.selectbox(
                "Select PDF file:",
                options=available_pdfs,
                help="Generate testset from this PDF only"
            )
            
            # Show info about selected PDF
            st.info(f"⚡ **Fast Mode Enabled** - Generating testset from: `{selected_pdf}`")
            st.caption(f"✓ Estimated time: 2-3 minutes | ✓ Lower token usage")
        else:
            st.warning(f"⚠️ **All Documents Mode** - Will process all {len(available_pdfs)} PDF(s)")
            st.caption(f"⏱️ This may take {len(available_pdfs) * 2}-{len(available_pdfs) * 4} minutes")
            
            # Show list of files that will be processed
            with st.expander(f"📋 PDFs to be processed ({len(available_pdfs)} files)"):
                for idx, pdf in enumerate(available_pdfs, 1):
                    st.text(f"{idx}. {pdf}")
        
        st.markdown("---")
        st.markdown("### ⚙️ Testset Configuration")
        
        testset_size = st.slider(
            "Number of test questions to generate",
            min_value=5,
            max_value=50,
            value=10,
            step=5,
            help="More questions take longer to generate but provide better evaluation coverage"
        )
        
        save_to_disk = st.checkbox(
            "Save to disk",
            value=True,
            help="Save testset and knowledge graph to 'testsets' folder"
        )
        
        # Generate button
        if st.button("🚀 Generate Testset", type="primary", use_container_width=True):
            with st.spinner("🤔 Generating testset... This may take a few minutes..."):
                result = generate_testset(testset_size, save_to_disk, selected_pdf)
                
                if result.get("status") == "success":
                    st.success(f"✅ {result.get('message')}")
                    
                    metadata = result.get("metadata", {})
                    testset_data = result.get("testset", [])
                    
                    # Display metadata
                    st.markdown("### 📊 Generation Statistics")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Questions", metadata.get("testset_size", 0))
                    col2.metric("Source Chunks", metadata.get("total_chunks", 0))
                    col3.metric("KG Nodes", metadata.get("kg_nodes", 0))
                    col4.metric("KG Relations", metadata.get("kg_relationships", 0))
                    
                    # Show source info
                    if metadata.get("source_file") and metadata.get("source_file") != "all_files":
                        st.info(f"📄 Generated from: **{metadata.get('source_file')}**")
                    else:
                        st.info(f"🌐 Generated from: **All {len(available_pdfs)} PDF(s)**")
                    
                    if save_to_disk:
                        st.info(f"📁 Files saved in `testsets/` folder")
                        if metadata.get("testset_path"):
                            st.code(metadata.get("testset_path"))
                    
                    # Display testset preview
                    st.markdown("### 📋 Generated Testset Preview")
                    
                    if testset_data:
                        import pandas as pd
                        df = pd.DataFrame(testset_data)
                        
                        st.dataframe(
                            df,
                            use_container_width=True,
                            height=400
                        )
                        
                        # Show detailed view
                        st.markdown("### 🔍 Detailed Question View")
                        
                        for idx, row in enumerate(testset_data[:5], 1):  # Show first 5
                            with st.expander(f"Question {idx}: {row.get('user_input', 'N/A')[:80]}..."):
                                st.markdown(f"**Question:** {row.get('user_input', 'N/A')}")
                                
                                if 'reference' in row:
                                    st.markdown(f"**Reference Answer:** {row.get('reference', 'N/A')}")
                                
                                if 'reference_contexts' in row:
                                    st.markdown("**Reference Contexts:**")
                                    contexts = row.get('reference_contexts', [])
                                    if isinstance(contexts, list):
                                        for i, ctx in enumerate(contexts, 1):
                                            st.text_area(
                                                f"Context {i}",
                                                value=ctx[:500] + "..." if len(str(ctx)) > 500 else str(ctx),
                                                height=100,
                                                key=f"ctx_{idx}_{i}"
                                            )
                        
                        if len(testset_data) > 5:
                            st.info(f"Showing 5 of {len(testset_data)} questions. View full testset in the CSV file.")
                    
                else:
                    st.error(f"❌ Generation failed: {result.get('message', 'Unknown error')}")
        
        # Show previously generated testsets
        st.markdown("---")
        st.markdown("### 📚 Previously Generated Testsets")
        
        testset_files = get_testset_files()
        
        if testset_files:
            st.info(f"Found {len(testset_files)} testset file(s)")
            
            # Add selector to load and view a testset
            selected_file = st.selectbox(
                "Select a testset to view:",
                options=[None] + [f["filename"] for f in testset_files[:20]],
                format_func=lambda x: "-- Choose a testset --" if x is None else x
            )
            
            if selected_file:
                # Find the selected file info
                file_info = next((f for f in testset_files if f["filename"] == selected_file), None)
                
                if file_info:
                    from datetime import datetime
                    modified_time = datetime.fromtimestamp(file_info.get("modified", 0))
                    
                    # Display file metadata
                    col1, col2, col3 = st.columns(3)
                    col1.metric("File Size", f"{file_info.get('size', 0) / 1024:.1f} KB")
                    col2.metric("Created", modified_time.strftime("%Y-%m-%d"))
                    col3.metric("Time", modified_time.strftime("%H:%M:%S"))
                    
                    # Load and display the testset
                    try:
                        import pandas as pd
                        testset_path = file_info.get("path", f"testsets/{selected_file}")
                        df = pd.read_csv(testset_path)
                        
                        st.success(f"✅ Loaded {len(df)} questions from testset")
                        
                        # Display testset table
                        st.markdown("#### 📊 Testset Overview")
                        st.dataframe(
                            df,
                            use_container_width=True,
                            height=300
                        )
                        
                        # Download button
                        csv_data = df.to_csv(index=False)
                        st.download_button(
                            label="⬇️ Download Testset CSV",
                            data=csv_data,
                            file_name=selected_file,
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        # Show detailed view of questions
                        st.markdown("#### 🔍 Detailed Question View")
                        
                        # Paginate questions
                        questions_per_page = 5
                        total_questions = len(df)
                        total_pages = (total_questions + questions_per_page - 1) // questions_per_page
                        
                        if total_pages > 1:
                            page = st.number_input(
                                "Page",
                                min_value=1,
                                max_value=total_pages,
                                value=1,
                                help=f"Showing {questions_per_page} questions per page"
                            )
                        else:
                            page = 1
                        
                        start_idx = (page - 1) * questions_per_page
                        end_idx = min(start_idx + questions_per_page, total_questions)
                        
                        for idx in range(start_idx, end_idx):
                            row = df.iloc[idx]
                            question_num = idx + 1
                            
                            with st.expander(f"Question {question_num}: {row.get('user_input', 'N/A')[:100]}...", expanded=(idx == start_idx)):
                                st.markdown(f"**❓ Question:** {row.get('user_input', 'N/A')}")
                                
                                if 'reference' in row:
                                    st.markdown(f"**✅ Reference Answer:**")
                                    st.info(row.get('reference', 'N/A'))
                                
                                if 'synthesizer_name' in row:
                                    st.caption(f"🔧 Generator: {row.get('synthesizer_name', 'Unknown')}")
                                
                                if 'reference_contexts' in row:
                                    st.markdown("**📚 Reference Contexts:**")
                                    contexts_str = str(row.get('reference_contexts', '[]'))
                                    try:
                                        import ast
                                        contexts = ast.literal_eval(contexts_str) if isinstance(contexts_str, str) else contexts_str
                                        if isinstance(contexts, list):
                                            for i, ctx in enumerate(contexts[:3], 1):  # Show first 3 contexts
                                                st.text_area(
                                                    f"Context {i}",
                                                    value=str(ctx)[:500] + "..." if len(str(ctx)) > 500 else str(ctx),
                                                    height=100,
                                                    key=f"loaded_ctx_{idx}_{i}"
                                                )
                                            if len(contexts) > 3:
                                                st.caption(f"+ {len(contexts) - 3} more contexts...")
                                    except:
                                        st.text_area("Contexts", value=contexts_str[:500], height=100)
                        
                        if total_pages > 1:
                            st.caption(f"Showing questions {start_idx + 1}-{end_idx} of {total_questions}")
                    
                    except Exception as e:
                        st.error(f"❌ Failed to load testset: {str(e)}")
            else:
                # Show list of available files
                st.markdown("#### Available testsets:")
                for file_info in testset_files[:10]:
                    from datetime import datetime
                    modified_time = datetime.fromtimestamp(file_info.get("modified", 0))
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.text(f"📄 {file_info.get('filename', 'Unknown')}")
                    col2.text(f"{file_info.get('size', 0) / 1024:.1f} KB")
                    col3.text(modified_time.strftime("%Y-%m-%d %H:%M"))
        else:
            st.info("No testsets generated yet. Generate your first testset above!")
    
    else:  # Query Documents tab
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
        
        # Chat History section for Query tab only
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
