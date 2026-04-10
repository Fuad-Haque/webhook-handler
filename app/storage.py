from typing import Optional

# In-memory storage
users_db: dict = {}
events_log: list = []
processed_event_ids: set = set()
_next_user_id: int = 1


# ── User helpers ─────────────────────────────────────────────────────────────

def get_user_by_username(username: str) -> Optional[dict]:
    return users_db.get(username)


def get_user_by_email(email: str) -> Optional[dict]:
    for user in users_db.values():
        if user["email"] == email:
            return user
    return None


def add_user(user_dict: dict) -> dict:
    global _next_user_id
    user_dict["id"] = _next_user_id
    _next_user_id += 1
    users_db[user_dict["username"]] = user_dict
    return user_dict


# ── Event helpers ─────────────────────────────────────────────────────────────

def add_event(event_dict: dict) -> None:
    events_log.append(event_dict)


def mark_processed(event_id: str) -> None:
    processed_event_ids.add(event_id)


def is_processed(event_id: str) -> bool:
    return event_id in processed_event_ids


def get_event_by_id(event_id: str) -> Optional[dict]:
    for event in events_log:
        if event["id"] == event_id:
            return event
    return None


def update_event(event_id: str, updates: dict) -> None:
    for event in events_log:
        if event["id"] == event_id:
            event.update(updates)
            return