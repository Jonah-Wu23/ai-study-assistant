# ai-study-assistant
## Introduction
ai-study-assistant is an AI learning assistance platform built based on local GraphRAG. It supports document ingestion, semantic retrieval, and streaming conversations, enabling users to quickly build personalized knowledge bases and efficiently complete learning tasks.

Exsample: http://162.14.126.29/

## Core Functions
- Document Ingestion: Supports the import of multiple text format files, automatically slices them, and constructs vector indexes.
- Semantic Retrieval: Based on the GraphRAG engine, it can quickly locate relevant document segments.
- Intelligent Conversation: Generates answers in combination with large language models and supports streaming output (SSE).
- Topic Management: Isolates multiple conversations and supports topic creation, query, and deletion.
- Front - end Interaction: An intuitive chat UI that supports file uploads, topic lists, and viewing of chat history.

## Technology Stack
- Back - end: FastAPI + Uvicorn
- Retrieval Engine: Localized implementation of GraphRAG
- Storage: Local file system (data/, vector_store/, chat_history/)
- Front - end: Vite + Vue3/React
- Dependency Management: Python requirements.txt, npm package.json

## Project Structure
When running for the first time, it needs to be constructed according to the following project structure:
```
ai-study-assistant/
├── backend/
│   ├── main.py                 # FastAPI application entry
│   ├── graphrag_processor.py   # GraphRAG initialization and ingestion logic
│   ├── storage.py              # File storage and topic management
│   ├── models.py               # Data model definition
│   ├── data/                   # Original document directory
│   ├── vector_store/           # Vector index storage
│   ├── embedding_models_cache_zh/ # Embedding model cache
│   ├── chat_history/           # Chat history records
│   ├── .env                    # Environment variable configuration
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── public/                 # Static resources
│   ├── src/                    # Front - end source code
│   │   └── services/api.js     # API call encapsulation
│   ├── vite.config.js          # Vite configuration
│   └── package.json            # Front - end dependencies and scripts
├── .gitignore
├── README.md
└── run.bat                     # Startup script
```

## Installation and Running
Manually create a .env file in backend/.env. The content is as follows:
```bash
# .env
COURSE_MATERIAL_DIR=./data
CHAT_HISTORY_DIR=./chat_history
GRAPHRAG_ROOT_DIR=./data # Root for graphrag files

# DeepSeek Credentials (Used by graphrag_processor to create settings.yaml)
DEEPSEEK_API_KEY=YourDeepSeekApiKey
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# PORT=8000 # Optional: Define server port
```

### Back - end
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Front - end
```bash
cd frontend
npm install
npm run dev
```
Access http://localhost:5173 to use the front - end interface.
When using it for the second time, you can directly start it using run.bat.

## Usage Instructions
1. Place the target documents in the `backend/data/` directory.
2. Call the back - end `/api/ingest` interface to generate retrieval indexes.
3. Enter queries in the front - end chat interface, and the system will return relevant content and support streaming conversations.
4. Use test interfaces such as `/api/test-delete/{item_id}` to verify the deletion function.

## Contribution Guidelines
1. Fork this repository.
2. Create a branch `feat/xxx`.
3. Submit code and initiate a Pull Request.

## License
This project uses the MIT License. Please refer to the LICENSE file for details. 