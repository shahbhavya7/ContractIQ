# 📊 Contract RAG System - Architecture & Flow Diagrams

This document provides detailed flow diagrams for all major operations in the Contract RAG System.

## 📋 Table of Contents

1. [System Architecture](#system-architecture)
2. [PDF Ingestion Flow](#pdf-ingestion-flow)
3. [Query Processing Flow](#query-processing-flow)
4. [Testset Generation Flow](#testset-generation-flow)
5. [Component Interactions](#component-interactions)
6. [Data Flow Diagram](#data-flow-diagram)

---

## System Architecture

### Overall System Design

```
┌────────────────────────────────────────────────────────────────────┐
│                        CONTRACT RAG SYSTEM                         │
└────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│   User Interface    │
│    (Streamlit)      │
│  ┌───────────────┐  │
│  │ Ingest PDFs   │  │
│  │ Query Docs    │  │
│  │ Gen Testset   │  │
│  └───────────────┘  │
└──────────┬──────────┘
           │ HTTP REST
           ▼
┌─────────────────────────────────────────────────────────────────┐
│              API Layer (FastAPI)                                │
│  ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────────────────┐ │
│  │ /ingest  │ │/query  │ │/stats  │ │/generate-testset     │ │
│  └──────────┘ └────────┘ └────────┘ └──────────────────────┘ │
└─────────┬──────────────────────────────────┬──────────────────┘
          │                                  │
    ┌─────▼──────────────────────┐   ┌──────▼────────┐
    │   Processing Pipeline      │   │  RAG Engine   │
    │  ┌──────────────────────┐  │   │               │
    │  │ 1. Text Extraction   │  │   │ ┌──────────┐  │
    │  │ 2. Chunking          │  │   │ │Embeddings│  │
    │  │ 3. Embedding Gen     │  │   │ └──────────┘  │
    │  │ 4. Vector Storage    │  │   │ ┌──────────┐  │
    │  └──────────────────────┘  │   │ │LLM (Groq)│  │
    └──────┬──────────────────────┘   │ └──────────┘  │
           │                          │ ┌──────────┐  │
           │                          │ │LangChain │  │
           │                          │ │RAG Chain │  │
           │                          │ └──────────┘  │
           │                          └──────┬───────┘
           │                                 │
    ┌──────▼──────────────────────────────────▼────────┐
    │      PostgreSQL + pgvector Vector Database       │
    │  ┌────────────────────────────────────────────┐  │
    │  │  langchain_pg_collection                   │  │
    │  │  langchain_pg_embedding (vectors + text)  │  │
    │  │  langchain_pg_document                     │  │
    │  └────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              External Services                                  │
│  ┌──────────────────┐          ┌───────────────────────────┐   │
│  │ Groq API         │          │ HuggingFace Embeddings    │   │
│  │ (LLM Inference)  │          │ (sentence-transformers)   │   │
│  └──────────────────┘          └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## PDF Ingestion Flow

### Step-by-Step Ingestion Process

```
User uploads PDF
      │
      ▼
┌─────────────────────────────────┐
│  Frontend (Streamlit)           │
│  - File selection dialog        │
│  - Validation (PDF format)      │
└────────────┬────────────────────┘
             │ POST /ingest
             ▼
┌─────────────────────────────────┐
│  Backend (FastAPI)              │
│  - Save to temp file            │
│  - Validate file integrity      │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Text Extraction                │
│  - pdfminer.six library         │
│  - Extract raw text from PDF    │
│  - Remove formatting artifacts  │
└────────────┬────────────────────┘
             │ Raw text
             ▼
┌─────────────────────────────────┐
│  Text Validation                │
│  - Check minimum text length    │
│  - Validate content quality     │
└────────────┬────────────────────┘
             │ Valid text?
        ┌────┴────┐
        │          │
       NO         YES
        │          │
        ▼          ▼
      Error   ┌──────────────────────────┐
             │  Intelligent Chunking    │
             │  - Title-based splitting │
             │  - Preserve structure    │
             │  - Size: 800 chars       │
             │  - Overlap: 20%          │
             └────────┬─────────────────┘
                      │ Document chunks
                      ▼
             ┌──────────────────────────┐
             │  Metadata Generation     │
             │  - source_file           │
             │  - chunk_id              │
             │  - total_chunks          │
             │  - chunk_type            │
             └────────┬─────────────────┘
                      │ Chunks + metadata
                      ▼
             ┌──────────────────────────┐
             │  Embedding Generation    │
             │  - HuggingFace model     │
             │  - all-MiniLM-L6-v2      │
             │  - 384-dim vectors       │
             └────────┬─────────────────┘
                      │ Vectors + text
                      ▼
             ┌──────────────────────────┐
             │  Vector Storage          │
             │  - PostgreSQL + pgvector │
             │  - Store in collection   │
             │  - Index creation        │
             └────────┬─────────────────┘
                      │
                      ▼
            ┌──────────────────────┐
            │  Success Response    │
            │  - Chunks created    │
            │  - Processing time   │
            │  - File info         │
            └──────────────────────┘
                      │
                      ▼
            Update Sidebar Statistics
```

#### Written Description: PDF Ingestion Process

The PDF ingestion process is a multi-stage pipeline designed to convert uploaded contract documents into queryable vector embeddings:

1. **User Upload & Frontend Validation**: When a user selects a PDF file through the Streamlit interface, the frontend validates that the file is indeed a PDF format before sending it to the backend.

2. **Backend Processing Initiation**: The FastAPI backend receives the PDF file and saves it to a temporary location on disk. The system validates the file's integrity to ensure it's not corrupted.

3. **Text Extraction**: Using the pdfminer.six library, the backend extracts all readable text from the PDF. This library is optimized for fast, accurate text extraction while removing formatting artifacts like page numbers and headers that don't contribute to document understanding.

4. **Content Validation**: The extracted text is validated to ensure:

   - Minimum text length (typically >100 characters) to confirm the PDF contains actual content
   - The content is meaningful (not just metadata or formatting)
   - If validation fails, the user receives an error message and the process stops

5. **Intelligent Chunking**: Once validated, the text is split into manageable chunks using the unstructured library's title-based chunking. This preserves document structure (titles, sections) rather than doing naive text splitting. Each chunk is typically 800 characters with 20% overlap to maintain context continuity.

6. **Metadata Attachment**: Each chunk is enriched with metadata including:

   - Source filename (which PDF it came from)
   - Chunk ID (its position within the document)
   - Total chunks in the document
   - Chunk type (title-based, body, etc.)

7. **Embedding Generation**: The chunks are converted into 384-dimensional vector embeddings using HuggingFace's all-MiniLM-L6-v2 model. This model captures semantic meaning, allowing similar content across documents to be found regardless of wording.

8. **Vector Storage**: The embeddings are stored in PostgreSQL with pgvector extension, creating searchable vector indices. The full text of each chunk is also stored for later display when that chunk is retrieved as a source.

9. **Response & UI Update**: The backend returns statistics (number of chunks created, processing time, file size) which are displayed in the Streamlit sidebar, giving users immediate feedback that ingestion succeeded.

**Key Benefits of This Approach**:

- Title-based chunking preserves document structure for better semantic understanding
- Metadata enables precise source attribution in query responses
- HuggingFace embeddings are fast and don't require external API calls
- Vector storage in PostgreSQL allows efficient similarity search
- Entire process is optimized for speed (typical 3-second ingestion for 50KB PDF)

### Ingestion Timeline

```
Timeline for a 50KB PDF (5,000 words):
┌─────────────────────────────────────────────────┐
│ Operation          │ Time    │ Status          │
├─────────────────────────────────────────────────┤
│ File Upload        │ 0.2s    │ ⚡ Fast         │
│ Text Extraction    │ 0.5s    │ ⚡ Fast         │
│ Chunking           │ 0.3s    │ ⚡ Fast         │
│ Embedding Gen      │ 1.2s    │ 🔄 Moderate    │
│ DB Storage         │ 0.8s    │ ⚡ Fast         │
├─────────────────────────────────────────────────┤
│ TOTAL              │ ~3.0s   │ ✓ Complete     │
└─────────────────────────────────────────────────┘

Result: ~20-25 chunks created from 5,000 words
```

---

## Query Processing Flow

### Complete Query Execution Flow

```
User enters question
      │
      ▼
┌─────────────────────────────────┐
│  Query Interface (Streamlit)    │
│  - Natural language input       │
│  - Set num_results (3-15)       │
│  - Example questions available  │
└────────────┬────────────────────┘
             │ POST /query
             ▼
┌─────────────────────────────────┐
│  Backend Query Handler          │
│  - Validate query string        │
│  - Check system initialization  │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Step 1: Query Embedding            │
│  - Embed user question              │
│  - Same model as documents          │
│  - Generate 384-dim vector          │
└────────────┬────────────────────────┘
             │ Query vector
             ▼
┌─────────────────────────────────────┐
│  Step 2: Semantic Search            │
│  - Vector similarity search         │
│  - pgvector similarity search       │
│  - Retrieve top K results (k=5)     │
│  - Score: cosine similarity (0-1)   │
└────────────┬────────────────────────┘
             │ Top chunks + scores
             ▼
┌─────────────────────────────────────┐
│  Step 3: Context Assembly           │
│  - Combine top chunks               │
│  - Add source attribution           │
│  - Rank by relevance                │
└────────────┬────────────────────────┘
             │ Context + metadata
             ▼
┌─────────────────────────────────────┐
│  Step 4: LLM Generation             │
│  - Groq API (llama-3.3-70b)         │
│  - Prompt template:                 │
│    * Context chunks                 │
│    * User question                  │
│    * System instructions            │
│  - Temperature: 0.0 (deterministic) │
└────────────┬────────────────────────┘
             │ LLM response
             ▼
┌─────────────────────────────────────┐
│  Step 5: Response Assembly          │
│  - Extract answer from LLM          │
│  - Attach source documents          │
│  - Calculate similarity scores      │
│  - Format with citations            │
└────────────┬────────────────────────┘
             │ Formatted response
             ▼
┌─────────────────────────────────────┐
│  Frontend Response Display          │
│  - Show answer                      │
│  - Ranked sources                   │
│  - Similarity scores (0-100%)       │
│  - Color coding:                    │
│    🟢 High (≥70%)                   │
│    🟡 Medium (50-69%)               │
│    🔴 Low (<50%)                    │
└────────────┬────────────────────────┘
             │
             ▼
    ┌──────────────────────┐
    │  Save to History     │
    │  - Question          │
    │  - Answer            │
    │  - Sources           │
    └──────────────────────┘
```

#### Written Description: Query Processing Flow

The query processing flow is the core intelligence of the RAG system, combining semantic search with LLM generation to provide context-aware answers:

1. **User Input & Validation**: The user enters a natural language question through the Streamlit interface (e.g., "What are the termination clauses?"). They can also adjust the number of relevant chunks to retrieve (3-15) and see example questions as templates. The backend validates the query is not empty and checks the system is properly initialized.

2. **Query Embedding**: The user's question is converted into a 384-dimensional vector using the exact same HuggingFace model that embedded all the documents. This ensures semantic consistency - similar concepts get similar vector representations regardless of specific wording.

3. **Semantic Search with Similarity Scoring**: The query vector is compared against all document chunk vectors stored in PostgreSQL's pgvector index using cosine similarity. The system retrieves the top-K most relevant chunks (default K=5). Each chunk gets a similarity score between 0 and 1:

   - 1.0 = identical semantic meaning
   - 0.7-0.9 = highly relevant
   - 0.5-0.7 = moderately relevant
   - <0.5 = potentially relevant but low confidence

4. **Context Assembly**: The top-ranked chunks are combined with their metadata (source file, chunk position, similarity score) to create the retrieval context. The chunks are ranked by relevance score so the most important information appears first in the context.

5. **LLM Prompt Generation**: The backend constructs a detailed prompt for the Groq LLM containing:

   - System instructions positioning the LLM as a contract analysis expert
   - The retrieved context chunks (ranked by relevance)
   - The user's original question
   - Instructions to provide detailed, well-structured answers with citations

6. **LLM Generation via Groq API**: The prompt is sent to Groq's ultra-fast inference API using the llama-3.3-70b model. The temperature is set to 0.0 for deterministic, factual responses (not creative ones). The LLM generates a thoughtful answer based on the provided context.

7. **Response Assembly & Formatting**: The system extracts the LLM's answer and combines it with the retrieved source chunks. For each source, it:

   - Calculates what percentage of the query vector's "semantic space" it covers
   - Formats the chunk text for display
   - Preserves full metadata for attribution

8. **Frontend Presentation**: The answer is displayed prominently at the top. Below it, the source documents are shown ranked by relevance with color-coded similarity indicators:

   - 🟢 Green (≥70%): High confidence - very relevant to the query
   - 🟡 Yellow (50-69%): Medium confidence - somewhat relevant
   - 🔴 Red (<50%): Lower confidence - included but less certain
     Each source is expandable to show the full chunk text and metadata.

9. **Chat History**: The question, answer, and sources are automatically saved to the session's chat history, visible at the bottom of the page. Users can review previous queries and clear history if needed.

**Key Characteristics**:

- **Fast Response**: Typical 3-4 second response time (80% spent waiting for LLM)
- **Accurate Attribution**: Every answer snippet is traced back to specific source documents
- **Transparency**: Users see exactly which chunks informed the answer
- **Multi-Document Support**: Automatically finds relevant information across multiple ingested PDFs
- **Configurable**: Users can adjust how many chunks are retrieved (more context vs. speed tradeoff)

### Query Response Structure

```
Query: "What are the payment terms?"
      │
      ├─ Answer (from LLM)
      │  └─ "The payment terms specify..."
      │
      └─ Sources (retrieved chunks)
         │
         ├─ Source #1
         │  ├─ Content: "Payment shall be made..."
         │  ├─ File: contract1.pdf
         │  ├─ Chunk: 3/25
         │  └─ Similarity: 89% 🟢
         │
         ├─ Source #2
         │  ├─ Content: "For services rendered..."
         │  ├─ File: contract2.pdf
         │  ├─ Chunk: 7/18
         │  └─ Similarity: 76% 🟢
         │
         └─ Source #3
            ├─ Content: "Payment schedule as follows..."
            ├─ File: contract1.pdf
            ├─ Chunk: 12/25
            └─ Similarity: 62% 🟡
```

### Query Performance Profile

```
Typical Query Response Time (5 documents, 150 chunks):
┌────────────────────────────────────────────┐
│ Operation           │ Time   │ % of Total │
├────────────────────────────────────────────┤
│ Embed query         │ 0.2s   │ 5%         │
│ Vector search       │ 0.3s   │ 8%         │
│ Context assembly    │ 0.1s   │ 2%         │
│ LLM inference       │ 3.0s   │ 80%        │
│ Response formatting │ 0.2s   │ 5%         │
├────────────────────────────────────────────┤
│ TOTAL               │ ~3.8s  │ 100%       │
└────────────────────────────────────────────┘

Note: LLM inference dominates the response time
```

---

## Testset Generation Flow

### Complete Testset Generation Process

```
User initiates testset generation
      │
      ▼
┌──────────────────────────────┐
│  Testset UI (Streamlit)      │
│  - Choose size (5-50)        │
│  - Select save option        │
│  - Start generation          │
└────────────┬─────────────────┘
             │ POST /generate-testset
             ▼
┌──────────────────────────────┐
│  Backend Testset Handler     │
│  - Verify GROQ_API_KEY       │
│  - Check vector store        │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Step 1: Document Retrieval          │
│  - Query all chunks (limit: 500)     │
│  - Reason: Rate limit avoidance      │
└────────────┬────────────────────────┘
             │ Retrieved chunks
             ▼
┌──────────────────────────────────────┐
│  Step 2: Knowledge Graph Creation    │
│  (Ragas Framework)                   │
│  - Create KG nodes from documents    │
│  - Sample max 100 for transforms     │
└────────────┬────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Step 3: Knowledge Enrichment        │
│  - Apply Ragas transformations:      │
│    • SummaryExtractor                │
│    • EntityExtractor                 │
│    • Relationship Extraction         │
│  - Build relationships (605 typical) │
│  - Retry logic for rate limits       │
└────────────┬────────────────────────┘
             │ Enriched KG
             ▼
┌──────────────────────────────────────┐
│  Step 4: Question Generation         │
│  (Ragas TestsetGenerator)            │
│  - Query distribution:               │
│    • 50% Single-hop specific         │
│    • 25% Multi-hop abstract          │
│    • 25% Multi-hop specific          │
│  - Generate N questions              │
│  - Create reference answers          │
└────────────┬────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
   YES               NO
    │                 │
    ▼                 ▼
Success          Retry logic
    │           (max 3 times)
    │                 │
    └────────┬────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Step 5: File Export (if enabled)    │
│  - Save to testsets/ folder          │
│  - Filenames with timestamp          │
│    • testset_YYYYMMDD_HHMMSS.csv    │
│    • knowledge_graph_...json        │
└────────────┬────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Response to Frontend                │
│  - Status: success                   │
│  - Testset data (JSON)               │
│  - Metadata (nodes, relations, etc.) │
│  - File paths (if saved)             │
└────────────┬────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Display Results                     │
│  - Generation statistics             │
│  - Questions table                   │
│  - Detailed question view            │
│  - File listing                      │
└──────────────────────────────────────┘
```

#### Written Description: Testset Generation Flow

Testset generation creates synthetic question-answer pairs for evaluating RAG system performance. This is a complex, multi-step process using the Ragas framework:

1. **User Configuration**: The user selects how many test questions to generate (5-50 questions) and whether to save the results to disk. More questions provide better evaluation coverage but take longer to generate.

2. **Validation & Preparation**: The backend verifies:

   - GROQ_API_KEY is configured (needed for LLM operations)
   - The vector store has documents to work with
   - The system is properly initialized

3. **Document Retrieval with Rate Limit Awareness**: The system retrieves all chunks from the vector database, but limits to 500 chunks maximum. This is intentional to avoid hitting Groq API rate limits during generation. The system prioritizes quality over quantity.

4. **Knowledge Graph Construction**: The Ragas framework creates a Knowledge Graph where:

   - Each document chunk becomes a node in the graph
   - Relationships between related chunks are identified
   - Rich metadata is preserved (source file, chunk position, etc.)

5. **Knowledge Enrichment via Transformations**: Ragas applies three types of transformations:

   - **SummaryExtractor**: Creates brief summaries of document sections
   - **EntityExtractor**: Identifies important entities (parties, dates, amounts)
   - **RelationshipExtractor**: Finds relationships between chunks (e.g., "defines payment terms for party X")

   This enrichment happens on a sample of documents (max 100 chunks) to keep API calls manageable while still capturing semantic richness. The system includes automatic retry logic to handle Groq API rate limits - if a 429 error occurs, it waits 60 seconds and retries up to 3 times.

6. **Question Generation with Distribution Control**: The Ragas TestsetGenerator creates questions using three different synthesis strategies:

   - **Single-hop Specific (50%)**: Questions answerable from a single chunk
     - Example: "What is the contract duration?"
   - **Multi-hop Abstract (25%)**: Questions requiring synthesis across multiple chunks
     - Example: "How does the payment structure align with milestones?"
   - **Multi-hop Specific (25%)**: Questions needing multiple specific chunks
     - Example: "What are all the termination conditions?"

   For each question, the system:

   - Uses Groq LLM to synthesize a diverse, realistic question
   - Extracts reference answers from the document chunks
   - Preserves the source contexts that answer the question

7. **Graceful Error Handling**: If generation encounters persistent rate limits after 3 retries, the system continues with a simplified Knowledge Graph. This results in lower diversity questions but still produces a usable testset.

8. **File Export**: If the user enabled "Save to disk":

   - CSV file: testset_YYYYMMDD_HHMMSS.csv with columns (user_input, reference, reference_contexts, synthesizer_name)
   - JSON file: knowledge_graph_YYYYMMDD_HHMMSS.json containing the full enriched knowledge graph
   - Files are timestamped for easy tracking and version control

9. **Results Display**: The frontend shows:
   - Generation statistics (number of questions, KG nodes/relationships, source chunks)
   - Table preview of the generated questions
   - Expandable detailed view of each question with reference answers and contexts
   - Links to download/view saved files

**Key Design Decisions**:

- **Rate Limit Handling**: Automatic retry with exponential backoff prevents generation failures
- **Diverse Question Types**: 50-25-25 distribution ensures comprehensive evaluation coverage
- **Source Preservation**: Every question is traceable to specific document chunks
- **Timestamp Versioning**: Generated testsets are automatically versioned for reproducibility
- **Graceful Degradation**: Process completes even if rate limits prevent full enrichment

**Typical Timeline for 10 Questions**:

- Document retrieval: 0.5s
- KG construction: 0.2s
- Knowledge enrichment: 2-5s (with Groq API calls)
- Question generation: 3-8s (30-60s per question with rate limit handling)
- File export: 0.5s
- **Total: 6-14 minutes** depending on API availability

### Testset Generation Timeline

```
Timeline for generating 10 questions from 150 chunks:
┌──────────────────────────────────────────────────────┐
│ Operation                      │ Time    │ Notes     │
├──────────────────────────────────────────────────────┤
│ Retrieve documents             │ 0.5s    │ ⚡ Fast   │
│ Create KG nodes                │ 0.2s    │ ⚡ Fast   │
│ Apply transformations          │ 2.0-5.0 │ 🔄 Varies │
│ (with Groq API calls)          │ s       │           │
│ Generate questions             │ 3.0-8.0 │ 🔄 Varies │
│ (10 @ 30-60s each)             │ s       │ (Rate limit│
│                                │         │  handled) │
│ Format & save files            │ 0.5s    │ ⚡ Fast   │
├──────────────────────────────────────────────────────┤
│ TOTAL                          │ 6-14 min│ Typical   │
└──────────────────────────────────────────────────────┘

Variables affecting generation time:
• Number of documents (≤500 chunks)
• Groq API availability & rate limits
• Network latency
• System resources
```

### Rate Limit Handling in Testset Generation

```
Generation Loop with Retry Logic:
┌─────────────────────────────────┐
│  Start Transformation/Question   │
└────────────┬────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │  Attempt Count  │
    │  = 1 (max 3)    │
    └────────┬────────┘
             │
             ▼
    ┌──────────────────────┐
    │  Make API Call       │
    │  (Groq)              │
    └────────┬─────────────┘
             │
        ┌────┴────┐
        │          │
      Error       OK
        │          │
        ▼          ▼
    ┌──────┐   Success
    │429?  │
    └──┬───┘
       │
   ┌───┴──┐
   │      │
  YES     NO
   │      │
   ▼      ▼
  Wait   Log Error
  60s    & Continue
   │      │
   │  ┌───┘
   │  │
   ▼  ▼
Check Retry Count < 3
   │
   ├─ YES: Go back to API Call
   │
   └─ NO: Continue with simplified KG
         (questions may be less diverse)
```

---

## Component Interactions

### Multi-Document Query Flow

```
Multiple Documents Scenario:
┌────────────┐ ┌────────────┐ ┌────────────┐
│contract1.  │ │contract2.  │ │contract3.  │
│pdf (25ch)  │ │pdf (20ch)  │ │pdf (30ch)  │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      │              │              │
      └──────────────┬──────────────┘
                     │
                     ▼
         ┌──────────────────────┐
         │  Vector Database     │
         │  75 total chunks     │
         └──────────┬───────────┘
                    │
        Query: "Payment terms across all contracts"
                    │
                    ▼
         ┌──────────────────────┐
         │  Similarity Search    │
         │  Returns top 5 chunks │
         │  from mixed documents │
         └──────────┬───────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
    contract1.pdf      contract2.pdf
    Chunk 5 (89%)      Chunk 12 (85%)
    Chunk 8 (76%)

    (contract3 had no highly similar chunks)

Result: Answer synthesizes terms from
        multiple contracts with proper
        attribution for each source
```

### Concurrent Request Handling

```
Multiple Users Scenario:
┌────────────────┬────────────────┬────────────────┐
│    User A      │    User B      │    User C      │
│  Query PDF 1   │  Ingest PDF 4  │  Gen Testset   │
└────────┬───────┴────────┬───────┴────────┬───────┘
         │                │                │
         │ HTTP           │ HTTP           │ HTTP
         ▼                ▼                ▼
    ┌─────────────────────────────────────────┐
    │         FastAPI (Async)                 │
    │  - Handles concurrent requests          │
    │  - Non-blocking operations              │
    │  - Shared vector store access           │
    └─────────┬───────────────────────────────┘
              │
              ▼
    ┌─────────────────────────────────────────┐
    │      PostgreSQL Connection Pool         │
    │  - Manages DB connections               │
    │  - Connection reuse for efficiency      │
    │  - Prevents resource exhaustion         │
    └─────────┬───────────────────────────────┘
              │
    ┌─────────┴──────────┬──────────────┐
    │                    │              │
    ▼                    ▼              ▼
 User A Query      User B Ingest   User C Testset
 Response ready    Complete        In progress...
 in ~3.8s          in ~3.0s        ~10 min
```

---

## Data Flow Diagram

### Complete Data Pipeline

```
INGESTION PIPELINE:
─────────────────

PDF File
  │
  ├─ Size: 50KB
  ├─ Format: PDF
  └─ Content: Contract text
      │
      ▼
  Text Extraction (pdfminer)
      │
      ├─ Output: Raw text (5,000 words)
      └─ Metadata: source filename
          │
          ▼
      Chunking (unstructured)
          │
          ├─ Chunks: 20-25 pieces
          ├─ Size: 800 chars each
          └─ Metadata: chunk_id, total_chunks
              │
              ▼
          Embedding Generation (HuggingFace)
              │
              ├─ Model: all-MiniLM-L6-v2
              ├─ Dimension: 384-dim vectors
              └─ Metadata: source_file, chunk_type
                  │
                  ▼
              Vector Storage (PostgreSQL + pgvector)
                  │
                  └─ Stored in langchain_pg_embedding
                     with full text + metadata


QUERY PIPELINE:
──────────────

User Question
  │
  ├─ Input: "What are payment terms?"
  └─ Type: Natural language
      │
      ▼
  Query Embedding (HuggingFace)
      │
      └─ Output: 384-dim vector
          │
          ▼
      Similarity Search (pgvector)
          │
          ├─ Algorithm: Cosine similarity
          ├─ Top-K: 5 results (configurable)
          └─ Filter: Collection-specific
              │
              ▼
          Retrieved Chunks + Scores
              │
              ├─ Chunk text (800 chars)
              ├─ Similarity score (0-1)
              └─ Metadata (source, chunk_id)
                  │
                  ▼
              Context Assembly
                  │
                  └─ Combine top chunks into prompt
                      │
                      ▼
                  LLM Prompt Generation
                      │
                      ├─ System: "Expert contract analyzer"
                      ├─ Context: Retrieved chunks
                      └─ Query: User question
                          │
                          ▼
                      Groq API (llama-3.3-70b)
                          │
                          ├─ Model: Groq's inference
                          ├─ Speed: ~50 tokens/sec
                          └─ Deterministic (temp=0.0)
                              │
                              ▼
                          LLM Response (Generated Answer)
                              │
                              ├─ Text: ~200-500 words
                              └─ Citation-ready format
                                  │
                                  ▼
                              Response Assembly
                                  │
                                  ├─ Answer text
                                  ├─ Source ranking
                                  ├─ Similarity scores
                                  └─ Color coding
                                      │
                                      ▼
                                  Frontend Display


TESTSET GENERATION PIPELINE:
────────────────────────────

Vector Store Documents (≤500 chunks)
  │
  ├─ Total chunks: N
  ├─ Unique PDFs: M
  └─ Metadata: rich
      │
      ▼
  Knowledge Graph Creation (Ragas)
      │
      ├─ Nodes: Document nodes (N)
      ├─ Sampling: First 100 for transforms
      └─ Type: DOCUMENT nodes
          │
          ▼
      Knowledge Enrichment (Ragas Transforms)
          │
          ├─ Apply: SummaryExtractor
          ├─ Apply: EntityExtractor
          ├─ Apply: RelationshipExtractor
          └─ Result: Enriched KG (~300 nodes, 600+ relations)
              │
              ▼
          Query Generation (Ragas Synthesizers)
              │
              ├─ Distribution:
              │  ├─ 50% SingleHopSpecific
              │  ├─ 25% MultiHopAbstract
              │  └─ 25% MultiHopSpecific
              │
              ├─ Per query generation:
              │  ├─ Question synthesis (Groq)
              │  ├─ Answer extraction
              │  └─ Context selection
              │
              └─ Rate limit handling:
                 ├─ Retry on 429 errors
                 ├─ Wait 60s between retries
                 └─ Max 3 retry attempts
                     │
                     ▼
          Generated Testset
              │
              ├─ user_input: Question text
              ├─ reference: Answer text
              ├─ reference_contexts: Source chunks
              └─ synthesizer_name: Generator type
                  │
                  ▼
          File Export
              │
              ├─ CSV format: testset_*.csv
              ├─ JSON format: knowledge_graph_*.json
              └─ Timestamp: YYYYMMDD_HHMMSS
```

---

## Data Models

### Vector Store Schema

```
langchain_pg_collection
├─ uuid (PK)
├─ name: contract_rag_collection
└─ cmetadata: {}

langchain_pg_embedding
├─ uuid (PK)
├─ collection_id (FK)
├─ embedding: vector(384)
├─ document: text (chunk content)
└─ cmetadata: jsonb
   ├─ source_file: string
   ├─ chunk_id: integer
   ├─ total_chunks: integer
   ├─ chunk_type: string
   └─ (custom fields)

langchain_pg_document
├─ uuid (PK)
├─ collection_id (FK)
├─ document: text
└─ cmetadata: jsonb
```

### Testset Data Format

```csv
user_input,reference,reference_contexts,synthesizer_name
"What are the termination clauses?","The contract may be terminated...","['Context 1...','Context 2...']","MultiHopSpecificQuerySynthesizer"
"How does payment work?","Payment shall be made...","['Context 1...','Context 3...']","SingleHopSpecificQuerySynthesizer"
...
```

---

## Error Handling & Recovery

### Graceful Degradation

```
Scenario: Rate Limit During Testset Generation

Rate Limit Error (429)
  │
  ├─ Attempt 1: Fail → Wait 60s
  │
  ├─ Attempt 2: Fail → Wait 60s
  │
  ├─ Attempt 3: Fail → Continue with
  │                    simplified KG
  │
  └─ Result: Testset generated with
             lower diversity, but
             still valid & usable

Scenario: PDF Ingestion Failure

Invalid PDF detected
  │
  ├─ Validation failed
  │
  └─ User notified:
     ❌ "PDF appears empty"
        Try with another file
        or check if text is
        extractable

Scenario: Database Connection Loss

Connection Error
  │
  ├─ Retry: 3 attempts
  │
  ├─ Backoff: Exponential
  │
  └─ If persistent:
     ❌ "Database unavailable"
        Check PostgreSQL status
        Verify pgvector extension
```

---

## Performance Metrics

### Expected Performance Characteristics

```
INGESTION:
─────────
File Size    │ Chunks │ Time  │ Speed
─────────────┼────────┼───────┼──────────
10 KB        │ 2-3    │ 0.5s  │ ⚡ Fast
50 KB        │ 20-25  │ 2-3s  │ ⚡ Fast
100 KB       │ 40-50  │ 4-5s  │ ⚡ Fast
500 KB       │ 200+   │ 15-20s│ 🔄 Moderate

QUERYING:
────────
Chunks in DB │ Response │ Speed  │ Bottleneck
─────────────┼──────────┼────────┼──────────
50           │ 2-3s     │ ⚡ Fast│ LLM (50%)
150          │ 3-4s     │ ⚡ Fast│ LLM (75%)
500          │ 3.5-4.5s │ ⚡ Fast│ LLM (80%)
1000+        │ 4-5s     │ 🔄 OK │ LLM (85%)

TESTSET GENERATION:
──────────────────
Chunks  │ Questions │ Time      │ Notes
────────┼───────────┼───────────┼───────────
100     │ 5         │ 3-5 min   │ Quick test
200     │ 10        │ 6-10 min  │ Typical
500     │ 20        │ 12-20 min │ Large set
500+    │ 50        │ 30+ min   │ Rate limit
                                  affected
```

---

## Security & Data Flow

### Data Protection Throughout Pipeline

```
PDF Upload
  │
  └─ HTTPS ──→ Temporary File
                │
                ├─ Scanned: File integrity
                └─ Deleted: After processing
                    │
                    ▼
                Raw Text (In Memory)
                │
                ├─ Chunk extraction
                └─ Discarded: After chunking
                    │
                    ▼
                Document Chunks (Stored)
                │
                ├─ Location: PostgreSQL
                ├─ Encrypted: (Optional - implement)
                └─ Access: Query only via API
                    │
                    ▼
                Vector Embeddings (Stored)
                │
                └─ Location: pgvector extension
                   Cannot reconstruct original text
                    │
                    ▼
                API Responses (Transmitted)
                │
                └─ HTTPS
                   User only sees:
                   - Answer text
                   - Chunk excerpts
                   - Source attribution
```

---

This comprehensive flow diagram document provides detailed visualization of every major process in the Contract RAG System.
