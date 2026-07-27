# Enterprise AI Knowledge & Analytics Platform (EAKAP)

> An enterprise-grade AI platform that combines Retrieval-Augmented Generation (RAG), Natural Language Analytics, Conversational Memory, Hybrid Search, and AI Governance into a modular, production-oriented architecture.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Architecture](https://img.shields.io/badge/Architecture-DDD%20%7C%20SOLID-green)
![Tests](https://img.shields.io/badge/Tests-83%20Passing-success)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

# Overview

Enterprise AI Knowledge & Analytics Platform (EAKAP) is a modular backend platform designed to help organizations build secure, scalable, and governable AI applications over enterprise knowledge.

Unlike traditional chatbot implementations, EAKAP integrates:

- Retrieval-Augmented Generation (RAG)
- Hybrid Search
- Conversational Memory
- Natural Language to SQL Analytics
- Enterprise AI Governance
- Metadata-driven Knowledge Management
- Data Quality & Governance concepts

The platform is designed using Domain-Driven Design (DDD), SOLID principles, and clean architecture to provide a production-ready foundation for enterprise AI systems.

---

# Why this project?

Large organizations struggle with:

- Enterprise knowledge scattered across systems
- Hallucinations from LLMs
- Lack of governance
- Limited conversational context
- Difficulty querying structured databases using natural language
- Poor explainability and observability

EAKAP addresses these challenges by combining enterprise architecture principles with modern Generative AI patterns.

---

# Architecture

```text
                   +----------------------+
                   |    User / Client     |
                   +----------+-----------+
                              |
                    REST / Streamlit UI
                              |
                +-------------+--------------+
                | Enterprise Query Engine    |
                +-------------+--------------+
                              |
         +--------------------+--------------------+
         |                                         |
         |                                         |
  Conversational Memory                    Governance Layer
         |                                         |
         +--------------------+--------------------+
                              |
                     Hybrid Retrieval
            (BM25 + Vector + Rank Fusion)
                              |
                  Context Builder / Prompting
                              |
                     LLM Provider Layer
                    (Ollama / Mock LLM)
                              |
                  Enterprise Knowledge Base
```

---

# Features

## Enterprise RAG

- Document ingestion pipeline
- Intelligent chunking
- Embeddings
- ChromaDB integration
- Prompt management
- Context builder

## Hybrid Retrieval

- Vector Search
- BM25 Search
- Rank Fusion
- Re-ranking

## Conversational AI

- Session management
- Stateful conversation memory
- Context compression
- Conversation history formatting

## Analytics Engine

- Natural Language → SQL
- SQL validation
- Schema inspection
- BI response generation

## Enterprise AI Governance

- Input guardrails
- Output guardrails
- PII detection
- PII redaction
- Governance telemetry

## Database Layer

- Metadata repository
- Business glossary
- Data quality rules
- Data stewardship
- Governance reference data

---

# Project Structure

```text
src/
│
├── analytics/
├── app/
├── common/
├── governance/
├── rag/
│   ├── context/
│   ├── embeddings/
│   ├── ingestion/
│   ├── llm/
│   ├── memory/
│   ├── retrieval/
│   ├── prompts/
│   └── pipeline/
│
tests/
docs/
db/
api/
```

---

# Technology Stack

| Category | Technology |
|-----------|------------|
| Language | Python |
| LLM | Ollama |
| Vector Database | ChromaDB |
| Retrieval | BM25 + Dense Retrieval |
| Architecture | DDD, SOLID |
| Testing | PyTest |
| Database | SQLite |
| Configuration | Environment Variables |
| Logging | Python Logging |

---

# Installation

```bash
git clone https://github.com/kartheek274/enterprise-ai-knowledge-analytics-platform.git

cd enterprise-ai-knowledge-analytics-platform

python -m venv .venv

source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

---

# Configuration

Create a `.env` file:

```text
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3
CHROMA_PATH=data/vector_store
```

---

# Running the Application

```bash
python -m src.app.main
```

---

# Running Tests

```bash
pytest -q
```

Expected:

```text
83 passed
```

---

# Roadmap

## ✅ Version 1.0

- Enterprise RAG
- Hybrid Retrieval
- Analytics Engine
- Conversational Memory
- AI Governance
- Testing

## 🚧 Version 1.1

- Streamlit Enterprise Console
- Interactive Chat
- Analytics Dashboard
- Session Browser

## 🚧 Version 1.2

- Docker
- Docker Compose
- CI/CD
- GitHub Actions

## 🚧 Version 2.0

- Authentication
- Multi-user Sessions
- RBAC
- Azure OpenAI
- AWS Bedrock
- Observability
- Production Deployment

---

# Screenshots

*(Will be added after the Streamlit UI is completed.)*

---

# Documentation

See the `/docs` directory for:

- Architecture Decisions
- Data Dictionary
- Governance Policies
- Integration Framework
- ER Diagram
- Standards & Operations

---

# Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Commit changes.
4. Open a Pull Request.

---

# License

MIT License

---

# Author

**Kartheek Jagarlamudi**

Senior Analytics Consultant | Data Governance | Enterprise AI | Generative AI | Machine Learning

---

## Future Vision

The long-term vision of EAKAP is to evolve into a full Enterprise AI Platform supporting:

- AI Knowledge Management
- Enterprise Search
- Data Governance
- AI Governance
- Intelligent Analytics
- Agentic AI
- Multi-Agent Collaboration
- Enterprise AI Observability