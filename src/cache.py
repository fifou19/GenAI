"""
Local cache to save multiple chat conversations.
"""
import json
import uuid
from datetime import datetime
from src.config import CHAT_CACHE_DIR, CACHE_FILE

CHAT_CACHE_DIR.mkdir(parents=True, exist_ok=True)



def _load_all_conversations() -> list[dict]:
    """Load all conversations from the cache file."""
    if not CACHE_FILE.exists():
        return []

    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_all_conversations(conversations: list[dict]) -> None:
    """Save all conversations to the cache file."""
    CACHE_FILE.write_text(
        json.dumps(conversations, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def load_all_conversations() -> list[dict]:
    """Load all conversations from the cache."""
    return _load_all_conversations()


def create_new_conversation() -> dict:
    """Create a new conversation and save it to the cache."""
    conversations = _load_all_conversations()

    new_conv = {
        "id": str(uuid.uuid4()),
        "title": "New conversation",
        "created_at": datetime.now().isoformat(),
        "messages": [],
        "chat_history": [],
    }

    conversations.insert(0, new_conv)
    _save_all_conversations(conversations)
    return new_conv


def get_conversation(conversation_id: str) -> dict | None:
    """Get a conversation by its ID."""
    conversations = _load_all_conversations()
    for conv in conversations:
        if conv["id"] == conversation_id:
            return conv
    return None


def save_conversation(conversation_id: str, messages: list[dict], chat_history: list[dict]) -> None:
    """Save a conversation with updated messages and chat history."""
    conversations = _load_all_conversations()

    for conv in conversations:
        if conv["id"] == conversation_id:
            conv["messages"] = messages
            conv["chat_history"] = chat_history

            # Prendre le premier message user comme titre
            for msg in messages:
                if msg.get("role") == "user" and msg.get("content"):
                    conv["title"] = msg["content"][:40]
                    break
            break
    else:
        # Si la conversation n'existe pas encore, on la crée
        new_conv = {
            "id": conversation_id,
            "title": "New conversation",
            "created_at": datetime.now().isoformat(),
            "messages": messages,
            "chat_history": chat_history,
        }

        for msg in messages:
            if msg.get("role") == "user" and msg.get("content"):
                new_conv["title"] = msg["content"][:40]
                break

        conversations.insert(0, new_conv)

    _save_all_conversations(conversations)


def delete_conversation(conversation_id: str) -> None:
    """Delete a conversation by its ID."""
    conversations = _load_all_conversations()
    conversations = [conv for conv in conversations if conv["id"] != conversation_id]
    _save_all_conversations(conversations)