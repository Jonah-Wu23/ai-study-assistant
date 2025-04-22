# storage.py

import os
import json
import uuid
import logging      # Added import (if not already present)
import traceback    # <-- ADD THIS IMPORT
from typing import List, Dict, Optional
from models import Message, Topic, TopicInfo
from dotenv import load_dotenv

load_dotenv()
CHAT_HISTORY_DIR = os.getenv("CHAT_HISTORY_DIR", "./chat_history")

# Setup logger if needed, or rely on main's logging
log = logging.getLogger(__name__)
if not log.hasHandlers():
     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


if not os.path.exists(CHAT_HISTORY_DIR):
    os.makedirs(CHAT_HISTORY_DIR)

def _get_topic_path(topic_id: str) -> str:
    """Gets the file path for a given topic ID."""
    # Ensure topic_id is safe for filenames (though UUIDs usually are)
    safe_topic_id = "".join(c for c in topic_id if c.isalnum() or c in ('-', '_')).rstrip()
    if not safe_topic_id: # Handle empty/invalid IDs
        raise ValueError("Invalid topic ID provided")
    return os.path.join(CHAT_HISTORY_DIR, f"{safe_topic_id}.json")

def save_topic(topic: Topic):
    """Saves a topic's data to a JSON file."""
    try:
        filepath = _get_topic_path(topic.id)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(topic.model_dump(), f, ensure_ascii=False, indent=4) # Use model_dump for Pydantic v2+
    except ValueError as ve: # Catch invalid topic ID from _get_topic_path
         log.error(f"Error saving topic due to invalid ID '{topic.id}': {ve}")
    except IOError as e:
        log.error(f"Error saving topic file {topic.id}: {e}")
    except Exception as e:
        log.error(f"Unexpected error saving topic {topic.id}: {e}")

def load_topic(topic_id: str) -> Optional[Topic]:
    """Loads a topic's data from a JSON file."""
    try:
        filepath = _get_topic_path(topic_id)
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return Topic(**data)
    except ValueError as ve: # Catch invalid topic ID
         log.error(f"Error loading topic due to invalid ID '{topic_id}': {ve}")
         return None
    except (IOError, json.JSONDecodeError) as e:
        log.error(f"Error loading or decoding topic file {topic_id}: {e}")
        # Consider renaming corrupted file?
        # try:
        #     os.rename(filepath, filepath + ".corrupted")
        # except OSError:
        #     pass
        return None
    except Exception as e:
        log.error(f"Unexpected error loading topic {topic_id}: {e}")
        return None


def create_new_topic(name: Optional[str] = None) -> Topic:
    """Creates a new topic object and saves it."""
    topic_id = str(uuid.uuid4())
    if not name:
         existing_topics = list_topics()
         name = f"Topic {len(existing_topics) + 1}"

    topic = Topic(id=topic_id, name=name, messages=[])
    save_topic(topic)
    log.info(f"Created new topic: {topic.id} - {topic.name}")
    return topic

def list_topics() -> List[TopicInfo]:
    """Lists all available topics by reading filenames."""
    topics = []
    if not os.path.exists(CHAT_HISTORY_DIR) or not os.path.isdir(CHAT_HISTORY_DIR):
         log.error(f"Chat history directory not found or not a directory: {CHAT_HISTORY_DIR}")
         return []
    try:
        for filename in os.listdir(CHAT_HISTORY_DIR):
            if filename.endswith(".json") and not filename.endswith(".corrupted"): # Ignore corrupted
                topic_id = filename[:-5]
                # Basic load just to get name/preview, faster than full load?
                # Or full load is fine if files aren't huge. Sticking with full load.
                topic = load_topic(topic_id)
                if topic:
                    preview = "New Topic"
                    # Find first user message for preview
                    first_user_msg = next((m.content for m in topic.messages if m.role == 'user'), None)
                    if first_user_msg:
                        preview = first_user_msg[:50] + ("..." if len(first_user_msg) > 50 else "")
                    # If no user message, find first assistant message
                    elif topic.messages:
                        first_assistant_msg = next((m.content for m in topic.messages if m.role == 'assistant'), None)
                        if first_assistant_msg:
                             preview = first_assistant_msg[:50] + ("..." if len(first_assistant_msg) > 50 else "")
                        else: # Fallback if only non-user/assistant messages exist? Unlikely.
                             preview = topic.messages[0].content[:50] + "..." if topic.messages[0].content else preview


                    topics.append(TopicInfo(id=topic.id, name=topic.name, preview=preview))

        # Sort topics by name (case-insensitive)
        topics.sort(key=lambda t: t.name.lower())
    except OSError as e:
        log.error(f"Error listing topics in {CHAT_HISTORY_DIR}: {e}")
    except Exception as e:
        log.error(f"Unexpected error listing topics: {e}")
    return topics

def add_message_to_topic(topic_id: str, message: Message) -> Optional[Topic]:
    """Adds a message to a topic and saves it."""
    # It might be slightly more efficient to load, modify, save in the endpoint
    # But this keeps storage logic together. Consider performance if needed.
    topic = load_topic(topic_id)
    if topic:
        topic.messages.append(message)
        save_topic(topic) # This handles potential save errors
        return topic
    else:
         log.warning(f"Attempted to add message to non-existent or unloadable topic: {topic_id}")
         return None

def delete_topic_file(topic_id: str) -> bool:
    """Deletes the JSON file associated with a topic ID.

    Returns:
        True if deletion was successful or file didn't exist, False on error.
    """
    try:
        filepath = _get_topic_path(topic_id) # Can raise ValueError
    except ValueError as ve:
        log.error(f"Error deleting topic due to invalid ID '{topic_id}': {ve}")
        return False # Treat invalid ID as failure to delete

    if not os.path.exists(filepath):
        log.warning(f"Attempted to delete non-existent topic file: {filepath}")
        return True # File is already gone

    try:
        log.info(f"Attempting to delete topic file: {filepath}")
        os.remove(filepath)
        # Verify deletion (optional sanity check)
        if not os.path.exists(filepath):
            log.info(f"Successfully deleted topic file: {filepath}")
            return True
        else:
            log.error(f"os.remove completed for {filepath} but file still exists!")
            return False
    except PermissionError as pe:
        log.error(f"PermissionError deleting topic file {filepath}: {pe}")
        return False
    except OSError as e:
        # Catch other OS-level errors (e.g., file locked)
        log.error(f"OSError deleting topic file {filepath}: {e}")
        return False
    except Exception as e:
        # Catch any other unexpected error
        log.error(f"Unexpected error deleting topic file {filepath}: {e}")
        log.debug(traceback.format_exc()) # Log traceback for unexpected errors
        return False