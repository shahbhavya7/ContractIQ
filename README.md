# 📄 Contract RAG System

A production-ready **Retrieval-Augmented Generation (RAG)** system specifically designed for analyzing contract documents. Built with FastAPI, Streamlit, PostgreSQL with pgvector, and powered by Groq's LLaMA models.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.45.1-red.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Features

### Core Capabilities

- **📤 PDF Ingestion**: Upload and process contract PDFs with automatic text extraction
- **🔍 Semantic Search**: Natural language querying with context-aware responses
- **🧪 Testset Generation**: Automated creation of evaluation datasets using Ragas
- **📊 Source Attribution**: Track which document chunks contributed to each answer
- **⚡ Fast Processing**: Optimized chunking and embedding pipeline
- **🐘 PostgreSQL + pgvector**: Persistent vector storage with efficient similarity search

### Technical Highlights

- **Intelligent Chunking**: Title-based chunking preserves document structure
- **Rate Limit Handling**: Automatic retry logic for API rate limits
- **Real-time Statistics**: Track ingested documents and collection metrics
- **Multi-Document Support**: Query across multiple contract documents simultaneously
- **Similarity Scoring**: Visual ranking of source relevance with color-coded indicators
- **Chat History**: Keep track of recent queries and responses

## 🏗️ Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Streamlit     │◄───────►│   FastAPI        │◄───────►│   PostgreSQL    │
│   Frontend      │  HTTP   │   Backend        │  SQL    │   + pgvector    │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │   Groq LLaMA     │
                            │   + HuggingFace  │
                            │   Embeddings     │
                            └──────────────────┘
```

### Components

**Backend (FastAPI)**

- RESTful API endpoints for document operations
- PDF text extraction with pdfminer.six
- Vector embedding generation and storage
- RAG chain orchestration with LangChain
- Ragas testset generation integration

**Frontend (Streamlit)**

- Interactive web interface
- PDF upload and management
- Query interface with example questions
- Testset generation dashboard
- Real-time statistics and metrics

**Database (PostgreSQL + pgvector)**

- Vector similarity search
- Document metadata storage
- Collection management
- Persistent data storage

**AI Models**

- **LLM**: Groq's llama-3.3-70b-versatile (configurable)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Framework**: LangChain for RAG orchestration

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+ with pgvector extension
- Groq API key (get one at [console.groq.com](https://console.groq.com))

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/shahbhavya7/Industry-RAG.git
   cd ContractRAG
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL with pgvector**

   ```sql
   CREATE DATABASE vect;
   CREATE USER vect WITH PASSWORD 'vect';
   GRANT ALL PRIVILEGES ON DATABASE vect TO vect;

   -- Connect to vect database
   \c vect
   CREATE EXTENSION vector;
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:

   ```bash
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=vect
   DB_PASSWORD=vect
   DB_NAME=vect
   COLLECTION_NAME=contract_rag_collection

   # Groq API (Required)
   GROQ_API_KEY=your_groq_api_key_here

   # LLM Configuration (Optional)
   LLM_MODEL=llama-3.3-70b-versatile
   TEMPERATURE=0.0
   NUM_RESULTS=5
   ```

5. **Start the backend**

   ```bash
   python backend.py
   ```

   The backend will start on `http://localhost:8000`

6. **Start the frontend** (in a new terminal)

   ```bash
   streamlit run frontend.py
   ```

   The frontend will open in your browser at `http://localhost:8501`

## 📖 Usage Guide

### 1. Ingesting Documents

1. Navigate to the **"📤 Ingest PDFs"** tab
2. Click "Browse files" and select one or more PDF contracts
3. Click "📥 Ingest All Files"
4. Wait for processing to complete
5. View ingestion statistics in the sidebar

### 2. Querying Documents

1. Navigate to the **"🔍 Query Documents"** tab
2. Enter your question in natural language
   - Example: "What are the termination clauses in these contracts?"
3. Adjust retrieval settings if needed (number of chunks)
4. Click "🔍 Search"
5. Review the AI-generated answer and source documents

**Query Tips:**

- Be specific in your questions
- Ask about clauses, terms, obligations, or parties
- Use the example questions as templates
- More retrieved chunks = more context but slower response

### 3. Generating Evaluation Testsets

1. Navigate to the **"🧪 Generate Testset"** tab
2. Choose the number of questions (5-50)
3. Enable "Save to disk" to keep files
4. Click "🚀 Generate Testset"
5. Review generated questions and download CSV

**Testset Features:**

- Automatically generates diverse question types
- Creates reference answers from your documents
- Exports to CSV for evaluation workflows
- Tracks generation statistics

See [TESTSET_GENERATION_GUIDE.md](TESTSET_GENERATION_GUIDE.md) for detailed instructions.

## 🔧 Configuration

### Environment Variables

| Variable          | Default                   | Description                |
| ----------------- | ------------------------- | -------------------------- |
| `DB_HOST`         | `localhost`               | PostgreSQL host            |
| `DB_PORT`         | `5432`                    | PostgreSQL port            |
| `DB_USER`         | `vect`                    | Database user              |
| `DB_PASSWORD`     | `vect`                    | Database password          |
| `DB_NAME`         | `vect`                    | Database name              |
| `COLLECTION_NAME` | `contract_rag_collection` | Vector collection name     |
| `GROQ_API_KEY`    | _(required)_              | Groq API key               |
| `LLM_MODEL`       | `llama-3.3-70b-versatile` | Groq model name            |
| `TEMPERATURE`     | `0.0`                     | LLM temperature (0.0-1.0)  |
| `NUM_RESULTS`     | `5`                       | Default chunks to retrieve |

### Available Groq Models

- `llama-3.3-70b-versatile` (default, best quality)
- `llama-3.1-70b-versatile`
- `mixtral-8x7b-32768`
- `gemma2-9b-it`

See [Groq documentation](https://console.groq.com/docs/models) for full list.

## 📊 API Documentation

### Endpoints

#### `GET /`

Health check and system status

**Response:**

```json
{
  "status": "running",
  "service": "Contract RAG Backend",
  "version": "1.0.0",
  "initialized": true
}
```

#### `POST /ingest`

Ingest a PDF document

**Request:** `multipart/form-data` with PDF file

**Response:**

```json
{
  "status": "success",
  "message": "PDF ingested successfully in 2.34s",
  "details": {
    "filename": "contract.pdf",
    "chunks_created": 25,
    "text_length": 12500,
    "processing_time": "2.34s"
  }
}
```

#### `POST /query`

Query the document collection

**Request:**

```json
{
  "query": "What are the payment terms?",
  "num_results": 5
}
```

**Response:**

```json
{
  "answer": "The payment terms specify...",
  "sources": [
    {
      "rank": 1,
      "content": "Payment shall be made...",
      "similarity_score": 0.89,
      "source_file": "contract.pdf",
      "chunk_id": 5,
      "total_chunks": 25
    }
  ]
}
```

#### `GET /stats`

Get collection statistics

**Response:**

```json
{
  "status": "success",
  "details": {
    "total_chunks": 150,
    "unique_pdfs": 6,
    "pdf_list": ["contract1.pdf", "contract2.pdf"]
  }
}
```

#### `POST /generate-testset`

Generate evaluation testset

**Request:**

```json
{
  "testset_size": 10,
  "save_to_disk": true
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Successfully generated 10 test questions",
  "testset": [...],
  "metadata": {
    "total_chunks": 150,
    "testset_size": 10,
    "kg_nodes": 300,
    "kg_relationships": 1200
  }
}
```

#### `DELETE /clear`

Clear all documents from collection

**Response:**

```json
{
  "status": "success",
  "message": "Collection cleared successfully"
}
```

## 🗂️ Project Structure

```
ContractRAG/
├── backend.py                      # FastAPI backend server
├── frontend.py                     # Streamlit web interface
├── testset_generator.py            # Ragas testset generation module
├── requirements.txt                # Python dependencies
├── .env                           # Environment configuration (create this)
├── .env.template                  # Environment template
├── README.md                      # This file
├── TESTSET_GENERATION_GUIDE.md    # Detailed testset guide
└── testsets/                      # Generated testsets (auto-created)
    ├── testset_20231117_143022.csv
    └── knowledge_graph_20231117_143022.json
```

## 🧪 Testing

### Manual Testing

1. **Ingest Test Document**

   ```bash
   curl -X POST "http://localhost:8000/ingest" \
     -F "file=@test_contract.pdf"
   ```

2. **Query Test**

   ```bash
   curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "What are the key terms?", "num_results": 3}'
   ```

3. **Generate Testset**
   ```bash
   curl -X POST "http://localhost:8000/generate-testset" \
     -H "Content-Type: application/json" \
     -d '{"testset_size": 5, "save_to_disk": true}'
   ```

### Automated Evaluation

Use generated testsets with Ragas metrics:

```python
from ragas import evaluate
from ragas.metrics import answer_relevancy, faithfulness

# Load your testset
import pandas as pd
testset = pd.read_csv("testsets/testset_20231117_143022.csv")

# Evaluate your RAG system
results = evaluate(
    dataset=testset,
    metrics=[answer_relevancy, faithfulness]
)
```

## ⚠️ Troubleshooting

### Common Issues

**1. Backend fails to start**

- Check PostgreSQL is running: `pg_isready`
- Verify pgvector extension: `psql -c "SELECT * FROM pg_extension WHERE extname='vector';"`
- Confirm GROQ_API_KEY is set in `.env`

**2. Rate limit errors**

- Reduce testset_size (try 5 instead of 10)
- Wait between generation attempts
- System automatically retries with 60s delays
- Consider upgrading Groq tier

**3. PDF ingestion fails**

- Ensure PDF contains extractable text (not scanned images)
- Check file is valid PDF format
- Try smaller files first (< 10MB)

**4. Slow query responses**

- Reduce num_results (try 3 instead of 5)
- Check database indexes
- Monitor Groq API latency

**5. Out of memory**

- Reduce chunk size in backend.py (`max_chars`)
- Limit documents per collection
- Use smaller embedding model

### Debug Mode

Enable detailed logging:

```python
# In backend.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Tips

1. **Optimize Chunk Size**: Balance between context and precision (default: 800 chars)
2. **Batch Ingestion**: Process multiple PDFs together for efficiency
3. **Database Indexing**: Ensure pgvector indexes are created
4. **Caching**: Embeddings model cached after first load
5. **Rate Limits**: Generate testsets during off-peak hours

## 🔐 Security Considerations

- Store API keys in `.env` file (never commit to git)
- Add `.env` to `.gitignore`
- Use environment-specific credentials
- Implement authentication for production deployments
- Sanitize user inputs
- Use HTTPS in production
- Regular security updates for dependencies

## 🛣️ Roadmap

- [ ] Support for more document formats (DOCX, TXT)
- [ ] User authentication and multi-tenancy
- [ ] Document comparison features
- [ ] Advanced filtering and search operators
- [ ] Export conversations to PDF/Word
- [ ] Integration with more LLM providers
- [ ] Batch query processing
- [ ] Custom chunking strategies
- [ ] Multilingual support

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Groq** for ultra-fast LLM inference
- **LangChain** for RAG framework
- **Ragas** for evaluation framework
- **pgvector** for efficient vector search
- **HuggingFace** for embedding models
- **FastAPI** and **Streamlit** for excellent frameworks

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/shahbhavya7/Industry-RAG/issues)
- **Discussions**: [GitHub Discussions](https://github.com/shahbhavya7/Industry-RAG/discussions)
- **Email**: shahbhavya7@example.com

## 🌟 Star History

If you find this project useful, please consider giving it a star ⭐!

---

**Built with ❤️ for contract analysis and RAG applications**

🚀 Powered by FastAPI + Streamlit | 🦙 Groq LLaMA | 🤗 HuggingFace | 🐘 PostgreSQL + pgvector
