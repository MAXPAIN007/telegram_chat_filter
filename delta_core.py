import copy
import json
from pathlib import Path


def message_sort_key(message: dict):
    return (
        str(message.get("date", "")),
        str(message.get("id", "")),
    )


def message_unique_key(message: dict):
    if "id" in message and message.get("id") is not None:
        return ("id", message["id"])

    return (
        "fallback",
        message.get("date"),
        message.get("from"),
        message.get("text"),
    )


def chat_unique_key(chat: dict):
    if "id" in chat and chat.get("id") is not None:
        return ("id", chat["id"])

    return ("name", str(chat.get("name", "")).casefold())


def merge_filtered_results(filtered_payloads: list[dict]) -> dict:
    merged_chats = {}

    for payload in filtered_payloads:
        for chat in payload.get("chats", []):
            key = chat_unique_key(chat)

            if key not in merged_chats:
                merged_chats[key] = {
                    "id": chat.get("id"),
                    "name": chat.get("name"),
                    "messages": copy.deepcopy(chat.get("messages", [])),
                }
                continue

            existing_chat = merged_chats[key]
            existing_messages = existing_chat["messages"]
            existing_keys = {message_unique_key(msg) for msg in existing_messages}

            for msg in chat.get("messages", []):
                msg_key = message_unique_key(msg)
                if msg_key not in existing_keys:
                    existing_messages.append(copy.deepcopy(msg))
                    existing_keys.add(msg_key)

    result_chats = list(merged_chats.values())

    for chat in result_chats:
        chat["messages"].sort(key=message_sort_key)

    result_chats.sort(
        key=lambda c: (
            str(c.get("name", "")).casefold(),
            str(c.get("id", "")),
        )
    )

    return {"chats": result_chats}


def load_json_if_exists(path: Path):
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compute_delta(previous_total: dict | None, current_total: dict):
    previous_chats = previous_total.get("chats", []) if previous_total else []
    current_chats = current_total.get("chats", [])

    previous_index = {
        chat_unique_key(chat): chat
        for chat in previous_chats
    }

    delta_chats = []
    delta_full_chats = []

    new_chats_count = 0
    updated_existing_chats_count = 0
    new_messages_count = 0

    for chat in current_chats:
        key = chat_unique_key(chat)
        previous_chat = previous_index.get(key)

        if previous_chat is None:
            full_chat = copy.deepcopy(chat)
            delta_chats.append(copy.deepcopy(full_chat))
            delta_full_chats.append(copy.deepcopy(full_chat))
            new_chats_count += 1
            new_messages_count += len(full_chat.get("messages", []))
            continue

        previous_message_keys = {
            message_unique_key(msg)
            for msg in previous_chat.get("messages", [])
        }

        new_messages = []
        for msg in chat.get("messages", []):
            msg_key = message_unique_key(msg)
            if msg_key not in previous_message_keys:
                new_messages.append(copy.deepcopy(msg))

        if new_messages:
            new_messages.sort(key=message_sort_key)

            delta_chats.append({
                "id": chat.get("id"),
                "name": chat.get("name"),
                "messages": new_messages,
            })

            delta_full_chats.append(copy.deepcopy(chat))
            updated_existing_chats_count += 1
            new_messages_count += len(new_messages)

    delta_chats.sort(
        key=lambda c: (
            str(c.get("name", "")).casefold(),
            str(c.get("id", "")),
        )
    )

    delta_full_chats.sort(
        key=lambda c: (
            str(c.get("name", "")).casefold(),
            str(c.get("id", "")),
        )
    )

    delta_payload = {"chats": delta_chats}
    delta_full_payload = {"chats": delta_full_chats}

    delta_stats = {
        "previous_total_chats": len(previous_chats),
        "current_total_chats": len(current_chats),
        "delta_chats": len(delta_chats),
        "delta_full_chats": len(delta_full_chats),
        "new_chats": new_chats_count,
        "updated_existing_chats": updated_existing_chats_count,
        "new_messages": new_messages_count,
        "first_run_without_previous_total": previous_total is None,
    }

    return delta_payload, delta_full_payload, delta_stats