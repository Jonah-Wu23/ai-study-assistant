from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    topic_id: str

class ChatResponse(BaseModel):
    reply: str
    topic_id: str # Confirm topic ID in response
    history: List[Message] # Return updated history

class NewTopicRequest(BaseModel):
    name: Optional[str] = None # Optional name for the new topic

class Topic(BaseModel):
    id: str
    name: str
    messages: List[Message] = []

class TopicInfo(BaseModel):
    id: str
    name: str
    preview: str # First message or default text