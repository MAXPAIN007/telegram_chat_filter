from pathlib import Path
import json


def norm(value):
    return str(value or "").strip().casefold()


def build_keywords_norm(keywords):
    return [norm(x) for x in keywords if norm(x)]


def is_personal_chat(chat: dict) -> bool:
    return norm(chat.get("type")) == "personal_chat"


def contains_keywords(text: str, keywords_norm: list[str]) -> bool:
    text_norm = norm(text)
    return any(keyword in text_norm for keyword in keywords_norm)


def chat_name_matches(chat: dict, keywords_norm: list[str]) -> bool:
    return contains_keywords(chat.get("name", ""), keywords_norm)


def first_messages_from_matches(
    chat: dict,
    keywords_norm: list[str],
    check_first_messages_from: bool,
    first_messages_limit: int,
) -> bool:
    if not check_first_messages_from:
        return False

    messages = chat.get("messages", [])
    if not isinstance(messages, list):
        return False

    checked = 0

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        sender = msg.get("from", "")
        if contains_keywords(sender, keywords_norm):
            return True

        checked += 1
        if checked >= first_messages_limit:
            break

    return False


def should_keep_chat(
    chat: dict,
    filter_mode: str,
    keywords_norm: list[str],
    only_personal_chats: bool,
    check_first_messages_from: bool,
    first_messages_limit: int,
) -> bool:
    if not isinstance(chat, dict):
        return False

    if only_personal_chats and not is_personal_chat(chat):
        return False

    matched_in_name = chat_name_matches(chat, keywords_norm)
    matched_in_from = first_messages_from_matches(
        chat,
        keywords_norm,
        check_first_messages_from,
        first_messages_limit,
    )

    matched = matched_in_name or matched_in_from

    if filter_mode == "exclude":
        return not matched

    if filter_mode == "include":
        return matched

    raise ValueError('filter_mode должен быть "include" или "exclude"')


def extract_text(message: dict) -> str:
    text = message.get("text", "")

    if isinstance(text, str):
        return text.strip()

    if isinstance(text, list):
        parts = []
        for item in text:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "".join(parts).strip()

    if text is None:
        return ""

    return str(text).strip()


def clean_message(message: dict):
    if not isinstance(message, dict):
        return None

    text = extract_text(message)
    if not text:
        return None

    cleaned = {}

    if "id" in message:
        cleaned["id"] = message["id"]

    if "reply_to_message_id" in message:
        cleaned["reply_to_message_id"] = message["reply_to_message_id"]

    if "date" in message:
        cleaned["date"] = message["date"]

    if "from" in message:
        cleaned["from"] = message["from"]

    cleaned["text"] = text

    return cleaned


def clean_chat(chat: dict, drop_chats_without_messages: bool):
    cleaned_messages = []

    for msg in chat.get("messages", []):
        cleaned_msg = clean_message(msg)
        if cleaned_msg is not None:
            cleaned_messages.append(cleaned_msg)

    if drop_chats_without_messages and not cleaned_messages:
        return None

    return {
        "id": chat.get("id"),
        "name": chat.get("name"),
        "messages": cleaned_messages,
    }


def filter_and_clean_export(
    data: dict,
    filter_mode: str,
    keywords: list[str],
    only_personal_chats: bool = False,
    check_first_messages_from: bool = True,
    first_messages_limit: int = 10,
    drop_chats_without_messages: bool = False,
):
    if not isinstance(data, dict):
        raise ValueError("Корень JSON должен быть объектом.")

    chats_obj = data.get("chats")
    if not isinstance(chats_obj, dict):
        raise ValueError('Не найден объект "chats".')

    chat_list = chats_obj.get("list")
    if not isinstance(chat_list, list):
        raise ValueError('Не найден список "chats.list".')

    keywords_norm = build_keywords_norm(keywords)

    total_chats = len(chat_list)
    kept_raw_chats = []
    excluded_chats = []

    for chat in chat_list:
        if should_keep_chat(
            chat=chat,
            filter_mode=filter_mode,
            keywords_norm=keywords_norm,
            only_personal_chats=only_personal_chats,
            check_first_messages_from=check_first_messages_from,
            first_messages_limit=first_messages_limit,
        ):
            kept_raw_chats.append(chat)
        else:
            excluded_chats.append({
                "id": chat.get("id"),
                "name": chat.get("name"),
                "type": chat.get("type"),
            })

    cleaned_chats = []
    for chat in kept_raw_chats:
        cleaned_chat = clean_chat(chat, drop_chats_without_messages)
        if cleaned_chat is not None:
            cleaned_chats.append(cleaned_chat)

    result = {
        "chats": cleaned_chats
    }

    stats = {
        "total_chats": total_chats,
        "kept_after_filter": len(kept_raw_chats),
        "excluded_after_filter": len(excluded_chats),
        "final_chats_in_output": len(cleaned_chats),
        "filter_mode": filter_mode,
        "keywords": keywords,
        "only_personal_chats": only_personal_chats,
        "check_first_messages_from": check_first_messages_from,
        "first_messages_limit": first_messages_limit,
        "drop_chats_without_messages": drop_chats_without_messages,
    }

    return result, stats, excluded_chats


def load_json_file(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)