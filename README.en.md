# ai-study-assistant

## Introduction

ai-study-assistant is an AI learning assistance platform built based on local GraphRAG. It supports document ingestion, semantic retrieval, and streaming conversations, helping users quickly build personalized knowledge bases and efficiently complete learning tasks.

## Core Functions

- Document Ingestion: Supports the import of various text format files, automatically fragments them, and builds vector indexes.
- Semantic Retrieval: Based on the GraphRAG engine, it can quickly locate relevant document fragments.
- Intelligent Conversation: Combines large language models to generate answers and supports streaming output (SSE).
- Topic Management: Isolates multiple conversations and supports topic creation, querying, and deletion.
- Frontend Interaction: An intuitive chat UI that supports file uploads, topic lists, and viewing of historical records.

## Technology Stack

- Backend: FastAPI + Uvicorn
- Retrieval Engine: Local implementation of GraphRAG
- Storage: Local file system (data/, vector_store/, chat_history/)
- Frontend: Vite + Vue3/React
- Dependency Management: Python requirements.txt, npm package.json

## Project Structure

```
ai-study-assistant/
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── graphrag_processor.py   # GraphRAG initialization and ingestion logic
│   ├── storage.py              # File storage and topic management
│   ├── models.py               # Data model definition
│   ├── data/                   # Directory for original documents
│   ├── vector_store/           # Vector index storage
│   ├── embedding_models_cache_zh/ # Embedding model cache
│   ├── chat_history/           # Chat history records
│   ├── .env                    # Environment variable configuration
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── public/                 # Static resources
│   ├── src/                    # Frontend source code
│   │   └── services/api.js     # API call encapsulation
│   ├── vite.config.js          # Vite configuration
│   └── package.json            # Frontend dependencies and scripts
├── .gitignore
├── README.md
└── run.bat                     # Startup script
```

## Installation and Running

### Backend
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Access http://localhost:5173 to use the frontend interface.

## Usage Instructions

1. Place the target document in the `backend/data/` directory.
2. Call the backend `/api/ingest` interface to generate a retrieval index.
3. Enter a query in the frontend chat interface, and the system will return relevant content and support streaming conversations.
4. Use test interfaces such as `/api/test-delete/{item_id}` to verify the deletion function.

## Contribution Guidelines

1. Fork this repository
2. Create a branch `feat/xxx`
3. Submit the code and initiate a Pull Request

## License

This project is licensed under the MIT License. For details, see the LICENSE file. 