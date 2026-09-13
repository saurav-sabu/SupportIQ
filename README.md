# SupportIQ 🛡️
### Autonomous Enterprise IT Support Agent powered by Agentic RAG

[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Pinecone](https://img.shields.io/badge/Pinecone-Serverless-000000?style=flat-square&logo=pinecone)](https://www.pinecone.io/)
[![Groq](https://img.shields.io/badge/Groq-Cloud-F55036?style=flat-square)](https://groq.com/)
[![Logfire](https://img.shields.io/badge/Pydantic-Logfire-E92063?style=flat-square)](https://logfire.pydantic.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

**SupportIQ** is an enterprise-grade AI technical support assistant that combines **Agentic Retrieval-Augmented Generation (Agentic RAG)**, self-correcting query refinement, private vector runbooks, and real-time web search fallback to deliver authoritative, grounded IT troubleshooting workflows.

---

## 🌟 Key Capabilities

* **Intelligent Intent Triage**: Automatically distinguishes between casual conversation, general support queries, and complex technical incidents requiring runbook retrieval.
* **Private Runbook Grounding**: Searches internal enterprise PDF, TXT, and Markdown guides stored in a Pinecone serverless vector index with semantic cosine similarity.
* **Evidence Quality Grading**: An LLM-powered evaluator assesses whether retrieved internal runbooks are sufficient to resolve the incident with high confidence.
* **Tavily Web Search Fallback**: Automatically escalates to verified external vendor documentation (Microsoft, Cisco, Apple, Dell, etc.) whenever internal runbooks lack specific error-code coverage.
* **Self-Correcting Query Rewriter**: Removes colloquialisms and extracts core technical entities, error codes, and operating systems to optimize retry searches.
* **Structured Enterprise Responses**: Formats troubleshooting runbooks with root-cause summaries, step-by-step instructions, syntax-highlighted PowerShell/CLI code blocks, safety prerequisites, verification checks, and escalation paths.
* **Glassmorphic Web Interface**: A modern, responsive single-page web console featuring interactive citations inspection, incident starter cards, live StateGraph execution path visualization, and dark/light themes.
* **Full-Stack Observability**: Built-in **Pydantic Logfire** auto-instrumentation across FastAPI routes, Pydantic schemas, and fine-grained LangGraph node spans, alongside **LangSmith** tracing.

---

## 🏗️ Agentic RAG Architecture

The workflow is orchestrated as an autonomous **StateGraph** in LangGraph:

```mermaid
flowchart TD
    Start([User Incident]) --> Route[route_question<br/>IT Service Desk Triage]
    
    Route -->|route == 'direct'| Direct[direct_answer<br/>Conversational Response]
    Route -->|route == 'kb'| RetrieveKB[retrieve_kb<br/>Pinecone Vector Search]
    
    RetrieveKB --> GradeKB[grade_kb_evidence<br/>QA Quality Grader]
    
    GradeKB -->|grade == 'good'| GenKB[generate_from_kb<br/>Private Runbook Synthesis]
    GradeKB -->|grade == 'weak'| SearchWeb[search_web<br/>Tavily Search Tool]
    
    SearchWeb --> GradeWeb[grade_web_evidence<br/>Web Technical Grader]
    
    GradeWeb -->|grade == 'good'| GenWeb[generate_from_web<br/>Web-Sourced Resolution]
    GradeWeb -->|grade == 'weak' & retries < max| Rewrite[rewrite_query<br/>Search Query Optimizer]
    GradeWeb -->|grade == 'weak' & retries >= max| Insufficient[answer_insufficient<br/>Tier-2 Escalation Advisory]
    
    Rewrite --> RetrieveKB
    
    Direct --> End([Structured Output + Citations])
    GenKB --> End
    GenWeb --> End
    Insufficient --> End
```

---

## 📂 Project Structure

```text
SupportIQ/
├── data/
│   └── ingest_kb/                  # Sample enterprise IT PDF runbooks
│       ├── 01_Network_Troubleshooting_Guide.pdf
│       ├── 02_Identity_Access_Support.pdf
│       ├── 03_Microsoft_365_Troubleshooting.pdf
│       ├── 04_Hardware_Troubleshooting.pdf
│       ├── 05_IT_Security_Incident_Guide.pdf
│       └── 06_IT_Service_Desk_Runbook.pdf
├── src/
│   ├── api/
│   │   └── routes.py               # FastAPI REST endpoints (/chat, /health, /kb/*)
│   ├── core/
│   │   ├── config.py               # Pydantic Settings & environment configuration
│   │   └── logging.py              # Logging & Pydantic Logfire initialization
│   ├── rag/
│   │   ├── state.py                # TypedDict AgentState & Pydantic decision models
│   │   ├── vectorstore.py          # Pinecone index & Google Gemini embeddings
│   │   └── workflow.py             # LangGraph StateGraph engine & prompt templates
│   ├── services/
│   │   ├── audit.py                # Audit logging service
│   │   └── ingestion.py            # Document loading, chunking & validation
│   └── main.py                     # FastAPI application entrypoint
├── static/
│   ├── css/
│   │   └── style.css               # Modern glassmorphic enterprise design system
│   └── js/
│       └── app.js                  # Frontend client controller & API integration
├── templates/
│   └── index.html                  # Main Web UI console template
├── ingest_kb.py                    # Standalone knowledge base batch ingestion script
├── requirements.txt                # Project dependencies
├── .env.example                    # Template environment variables
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites
* Python 3.11+
* Active API keys for:
  * **Groq Cloud** (LLM inference)
  * **Google Gemini** (embeddings: `gemini-embedding-2-preview`)
  * **Pinecone** (vector database)
  * **Tavily AI** (web search fallback)
  * *(Optional)* **Pydantic Logfire** (observability) & **LangSmith** (tracing)

### 2. Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/your-username/SupportIQ.git
cd SupportIQ

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory (based on `.env.example`):

```env
# LLM & Embedding Models
GROQ_API_KEY="gsk_..."
GROQ_MODEL="openai/gpt-oss-120b"
GOOGLE_API_KEY="AIzaSy..."
EMBEDDING_MODEL="gemini-embedding-2-preview"

# Vector Database (Pinecone)
PINECONE_API_KEY="pcsk_..."
PINECONE_INDEX_NAME="supportiq"
PINECONE_NAMESPACE="it-support-kb"

# Web Fallback Search
TAVILY_API_KEY="tvly-..."

# Security & Admin
ADMIN_API_KEY="supportiq-admin-2026"

# Observability (Optional)
LOGFIRE_TOKEN=""
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_API_KEY=""
LANGCHAIN_PROJECT="SupportIQ"

# Audit Logging Database (Optional: NeonDB / PostgreSQL)
# Leave empty to use local zero-config SQLite (data/audit.db)
DATABASE_URL=""

```

### 4. Ingest Sample Runbooks

Load and index the 6 enterprise IT runbooks into Pinecone:

```bash
python ingest_kb.py
```

### 5. Launch the Application

Start the FastAPI server:

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🖥️ Web Interface Features

| View | Features |
| :--- | :--- |
| **Support Console** | Interactive AI chat with real-time reasoning steps, markdown code blocks with 1-click copy buttons, grounded citation badges, prompt quick-starters, and transcript export. |
| **Knowledge Base Hub** | Drag-and-drop document ingestion for `.pdf`, `.txt`, and `.md` runbooks, real-time index status tags, instant search filtering, and 1-click batch reindexing. |
| **Agent Flow Visualizer** | Interactive flowchart of the LangGraph StateGraph pipeline, illuminating the exact decision path traversed for each query in real time. |
| **System Health** | Live latency counter, Pinecone telemetry, Groq model info, and Admin key configuration. |

---

## 📡 REST API Reference

Interactive OpenAPI documentation is available at **`/docs`**.

### `POST /api/chat`
Ask the Agentic RAG assistant a troubleshooting or general inquiry.

**Request Body:**
```json
{
  "question": "How do I troubleshoot VPN connection failing with Error 800?"
}
```

**Response:**
```json
{
  "answer": "### Diagnostic Summary\nVPN Error 800 indicates...",
  "source_used": "web",
  "citations": [
    {
      "source": "Microsoft Knowledge Base",
      "url": "https://learn.microsoft.com/...",
      "snippet": "Error 800 indicates the remote connection was not made..."
    }
  ],
  "rewritten_query": "How do I fix VPN error 800?"
}
```

### `GET /api/health`
Checks server heartbeat and vector index configuration.

### `GET /api/kb/documents`
Lists all active enterprise runbooks and uploaded guides.

### `GET /api/audit/logs`
Retrieves recent query and inference audit logs (timestamp, query, response summary, source used, latency) and identifies the active database provider (`NeonDB (PostgreSQL)` or `SQLite`).

### `POST /api/ingest`
Uploads and indexes a new runbook into Pinecone. Requires the `api_key` header matching `ADMIN_API_KEY`.

---

## 📊 Audit Logging with SQLAlchemy & NeonDB

SupportIQ includes a lightweight, zero-bloat audit logging system built entirely with **SQLAlchemy 2.0 ORM** for enterprise compliance and telemetry:

* **SQLAlchemy ORM Model**: Clean declarative `AuditLog` entity mapping `id`, `timestamp` (UTC), `question`, `answer`, `source_used` (`private_kb`, `web`, `direct`, `error`), and `latency_ms`. No manual SQL strings or driver quirks.
* **NeonDB (PostgreSQL)**: Connect your cloud Neon serverless database simply by setting `DATABASE_URL="postgresql://user:password@ep-something.neon.tech/neondb?sslmode=require"` in `.env`. Utilizes SQLAlchemy connection pooling (`pool_pre_ping=True`, `pool_recycle=300`) to handle Neon serverless auto-suspend seamlessly.
* **Live UI Console**: View recent audit entries directly in the System Health view with status pills, execution latency, and formatted question/answer summaries.



---

## 🔍 Observability with Pydantic Logfire


SupportIQ includes native instrumentation using [Pydantic Logfire](https://logfire.pydantic.dev/):

* **Automatic FastAPI Instrumentation**: Traces all incoming HTTP requests and response codes.
* **Pydantic Model Validation**: Spans automatically track serialization of `RouteDecision`, `EvidenceGrade`, and `ChatRequest`.
* **LangGraph Node Spans**: Every decision step (`rag.route_question`, `rag.retrieve_kb`, `rag.grade_kb_evidence`, `rag.search_web`, `rag.generate_from_kb`) produces OpenTelemetry trace spans with rich metadata attributes.

To stream traces to Logfire Cloud, simply add your token to `.env`:
```env
LOGFIRE_TOKEN="your-logfire-write-token"
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
