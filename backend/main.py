# main.py (Ensure async calls and handle ingestion)

from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import graphrag_processor # Using the new processor
import storage
from models import ChatRequest, ChatResponse, Message, NewTopicRequest, TopicInfo, Topic
from typing import List, Dict
import os
import uvicorn
import asyncio
import traceback # For detailed error logging
import json

# --- Application Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application starting up...")
    # Initialize GraphRAG Local Search Engine during startup
    await graphrag_processor.initialize_rag()
    yield
    print("Application shutting down...")

app = FastAPI(lifespan=lifespan, title="AI Study Assistant (GraphRAG Local Search)", version="1.2.0")

# --- CORS Middleware ---
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    # Add your frontend deployment URL here if applicable
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"], # Explicitly list allowed methods
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.get("/api/health", status_code=status.HTTP_200_OK)
async def health_check():
    # Check if GraphRAG initialized (simple check)
    init_status = "initialized" if graphrag_processor._initialized else "not_initialized"
    return {"status": "ok", "processor": "graphrag_local_search", "rag_status": init_status}

@app.post("/api/ingest", status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingestion_endpoint(request: Request):
    """Manually triggers the GraphRAG document ingestion process via CLI."""
    print("Received request to trigger GraphRAG ingestion via CLI...")
    try:
        # Run the CLI indexing in the background (fire and forget for the API response)
        # The actual indexing can take a long time.
        # The processor function now handles running the CLI command.
        asyncio.create_task(graphrag_processor.trigger_ingestion())
        return {"message": "GraphRAG indexing process started in background via CLI. Engine will reload data on next query/restart after completion."}

    except RuntimeError as re:
        print(f"Error during manual ingestion trigger: {re}")
        raise HTTPException(status_code=400, detail=str(re)) # Bad request if command not found etc.
    except Exception as e:
        print(f"Error during manual ingestion trigger: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ingestion trigger failed: {str(e)}")


# --- Topic Endpoints (No changes needed from previous version) ---
@app.get("/api/topics", response_model=List[TopicInfo])
async def get_topics():
    try: return storage.list_topics()
    except Exception as e: print(f"Error listing topics: {e}"); raise HTTPException(status_code=500, detail="Could not retrieve topics.")

@app.post("/api/topics", response_model=Topic, status_code=status.HTTP_201_CREATED)
async def create_topic(request: NewTopicRequest):
    try: return storage.create_new_topic(request.name)
    except Exception as e: print(f"Error creating topic: {e}"); raise HTTPException(status_code=500, detail="Could not create new topic.")

@app.get("/api/topics/{topic_id}", response_model=Topic)
async def get_topic_history(topic_id: str):
    topic = storage.load_topic(topic_id)
    if topic is None: raise HTTPException(status_code=404, detail="Topic not found.")
    return topic

# --- Message Endpoint (Using new query_rag) ---
@app.post("/api/topics/{topic_id}/messages")
async def post_message(topic_id: str, request: Request):
    """Handles a new user message, gets AI response using GraphRAG Local Search."""
    try:
        body = await request.json()
        user_message_content = body.get("message")
        if not user_message_content: raise HTTPException(status_code=400, detail="Missing 'message' field in request body.")
    except Exception as e: print(f"Error reading request body: {e}"); raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")

    print(f"Received message for topic {topic_id}: {user_message_content}")

    topic = storage.load_topic(topic_id)
    if topic is None: raise HTTPException(status_code=404, detail="Topic not found.")

    user_message = Message(role="user", content=user_message_content)
    storage.add_message_to_topic(topic_id, user_message)  # 立即保存用户消息
    
    # 定义流式生成响应的异步函数
    async def stream_response():
        try:
            # 为前端提供EventSource格式
            yield "data: {\"type\":\"start\", \"topicId\":\"" + topic_id + "\"}\n\n"
            
            # 准备历史记录（虽然在基本本地搜索中默认不使用）
            history_for_llm = [msg.dict() for msg in topic.messages[-10:]]  # 限制历史记录长度
            
            # 获取完整回复（非流式），然后模拟逐字输出
            full_ai_reply = await graphrag_processor.query_rag(user_message_content, history_for_llm)
            
            # 回复存储用
            ai_content_buffer = ""
            
            # 逐字发送回复（模拟流式）
            for char in full_ai_reply:
                ai_content_buffer += char
                yield f"data: {json.dumps({'type': 'chunk', 'content': char})}\n\n"
                await asyncio.sleep(0.02)  # 控制输出速度，每字符约20ms
            
            # 保存AI回复到存储
            ai_message = Message(role="assistant", content=full_ai_reply)
            storage.add_message_to_topic(topic_id, ai_message)
            
            # 获取更新后的完整历史记录
            updated_topic = storage.load_topic(topic_id)
            history_json = json.dumps([msg.dict() for msg in updated_topic.messages]) if updated_topic else "[]"
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'end', 'topicId': topic_id, 'history': history_json})}\n\n"
            
        except Exception as e:
            print(f"Error during GraphRAG query for topic {topic_id}: {e}")
            traceback.print_exc()  # 记录完整错误
            error_msg = f"抱歉，处理您的请求时发生内部错误。(Sorry, an internal error occurred while processing your request.)"
            
            # 保存错误消息
            ai_message = Message(role="assistant", content=error_msg)
            storage.add_message_to_topic(topic_id, ai_message)
            
            # 发送错误作为流式响应
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            
            # 获取更新后的历史记录
            updated_topic = storage.load_topic(topic_id)
            history_json = json.dumps([msg.dict() for msg in updated_topic.messages]) if updated_topic else "[]"
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'end', 'topicId': topic_id, 'history': history_json})}\n\n"
    
    # 返回流式响应
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 对Nginx很重要
        }
    )

@app.delete("/api/topics/{topic_id}", status_code=status.HTTP_200_OK)
async def delete_topic(topic_id: str):
    """Deletes a specific chat topic file."""
    print(f"Received request to delete topic: {topic_id}") # Keep this print

    # --- RESTORE THIS LOGIC ---
    deleted = storage.delete_topic_file(topic_id)
    if not deleted:
        topic_path = storage._get_topic_path(topic_id)
        if os.path.exists(topic_path): # Check if file still exists after failed delete attempt
             # Log the error clearly on the backend
             print(f"ERROR: storage.delete_topic_file reported failure for {topic_id}, and file still exists at {topic_path}. Raising 500.")
             raise HTTPException(status_code=500, detail=f"Could not delete topic file for ID: {topic_id}. Check backend logs for file system errors.")
        else:
             # File is gone now, even if delete_topic_file returned False (maybe race condition or it was already gone)
             print(f"Topic file for {topic_id} is gone now, proceeding as success.")
             pass # Proceed to return success message
    # --- END RESTORED LOGIC ---

    print(f"Successfully processed DELETE request for topic {topic_id}") # Keep this print
    return {"message": f"Topic {topic_id} deleted successfully."}

# --- ADD THIS NEW TEST ENDPOINT ---
@app.delete("/api/test-delete/{item_id}", status_code=status.HTTP_200_OK)
async def test_delete_endpoint(item_id: str):
    """A completely separate DELETE endpoint for testing."""
    print(f"--- DEBUG: Reached /api/test-delete/{item_id} endpoint! ---")
    return {"message": f"Successfully processed DELETE for test item {item_id}"}
# --- END OF NEW TEST ENDPOINT ---


# --- Run the server ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    reload_flag = os.getenv("RELOAD", "true").lower() == "true" # Control reload via env var
    print(f"Starting Uvicorn server on {host}:{port} (Reload: {reload_flag})...")
    uvicorn.run("main:app", host=host, port=port, reload=reload_flag)