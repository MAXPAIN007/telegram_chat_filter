import copy
import hashlib
import json
from datetime import date
from typing import Any

from parser_core import clean_message


FIELD_TYPES = {
    ("chat", "id"): "numeric",
    ("chat", "name"): "text",
    ("chat", "type"): "text",
    ("message", "id"): "numeric",
    ("message", "reply_to_message_id"): "numeric",
    ("message", "date"): "date",
    ("message", "from"): "text",
    ("message", "text"): "text",
}


CHAT_FIELDS = ["id", "name", "type"]
MESSAGE_FIELDS = ["id", "reply_to_message_id", "date", "from", "text"]


TEXT_OPERATORS = {
    "contains",
    "not_contains",
    "equals",
    "not_equals",
    "starts_with",
    "ends_with",
}

NUMERIC_OPERATORS = {
    "equals",
    "not_equals",
    "greater_than",
    "less_than",
}

DATE_OPERATORS = {
    "equals",
    "not_equals",
    "on_or_after",
    "on_or_before",
}


def norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def parse_date_only(value: str | None):
    raw = str(value or "").strip()
    if not raw:
        return None

    # Ожидаем либо YYYY-MM-DD, либо полный ISO c датой в начале
    raw = raw[:10]

    try:
        year, month, day = raw.split("-")
        return date(int(year), int(month), int(day))
    except Exception:
        return None


def normalize_filter_rule(rule: dict) -> dict:
    scope = str(rule.get("scope", "")).strip().lower()
    field = str(rule.get("field", "")).strip()
    operator = str(rule.get("operator", "")).strip().lower()
    mode = str(rule.get("mode", "include")).strip().lower()
    value = "" if rule.get("value") is None else str(rule.get("value")).strip()

    if scope not in {"chat", "message"}:
        raise ValueError(f'Некорректный scope: {scope}')

    if scope == "chat" and field not in CHAT_FIELDS:
        raise ValueError(f'Поле "{field}" недоступно для scope=chat')

    if scope == "message" and field not in MESSAGE_FIELDS:
        raise ValueError(f'Поле "{field}" недоступно для scope=message')

    field_type = FIELD_TYPES[(scope, field)]

    if field_type == "text" and operator not in TEXT_OPERATORS:
        raise ValueError(f'Оператор "{operator}" недоступен для текстового поля')

    if field_type == "numeric" and operator not in NUMERIC_OPERATORS:
        raise ValueError(f'Оператор "{operator}" недоступен для numeric поля')

    if field_type == "date" and operator not in DATE_OPERATORS:
        raise ValueError(f'Оператор "{operator}" недоступен для date поля')

    if mode not in {"include", "exclude"}:
        raise ValueError(f'Некорректный mode: {mode}')

    return {
        "scope": scope,
        "field": field,
        "operator": operator,
        "mode": mode,
        "value": value,
    }


def normalize_advanced_config(raw_config: dict) -> dict:
    match_mode = str(raw_config.get("match_mode", "all")).strip().lower()
    output_mode = str(raw_config.get("output_mode", "full_chats")).strip().lower()

    if match_mode not in {"all", "any"}:
        raise ValueError('match_mode должен быть "all" или "any"')

    if output_mode not in {"full_chats", "matched_messages_only"}:
        raise ValueError('output_mode должен быть "full_chats" или "matched_messages_only"')

    filters_raw = raw_config.get("filters", [])
    if not isinstance(filters_raw, list):
        raise ValueError("filters должен быть списком")

    normalized_filters = [normalize_filter_rule(rule) for rule in filters_raw]

    normalized = {
        "mode": "advanced",
        "match_mode": match_mode,
        "output_mode": output_mode,
        "date_from": str(raw_config.get("date_from", "") or "").strip(),
        "date_to": str(raw_config.get("date_to", "") or "").strip(),
        "filters": normalized_filters,
    }

    return normalized


def build_advanced_profile_id(config: dict) -> str:
    """
    Автоматический profile_id по hash от нормализованной конфигурации.
    """
    normalized = normalize_advanced_config(config)
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"adv_{digest}"


def get_field_value(target: dict, field: str):
    return target.get(field)


def apply_operator(field_value, operator: str, expected_value: str, field_type: str) -> bool:
    if field_type == "text":
        actual = norm(field_value)
        expected = norm(expected_value)

        if operator == "contains":
            return expected in actual
        if operator == "not_contains":
            return expected not in actual
        if operator == "equals":
            return actual == expected
        if operator == "not_equals":
            return actual != expected
        if operator == "starts_with":
            return actual.startswith(expected)
        if operator == "ends_with":
            return actual.endswith(expected)

    elif field_type == "numeric":
        try:
            actual = int(field_value)
            expected = int(expected_value)
        except Exception:
            return False

        if operator == "equals":
            return actual == expected
        if operator == "not_equals":
            return actual != expected
        if operator == "greater_than":
            return actual > expected
        if operator == "less_than":
            return actual < expected

    elif field_type == "date":
        actual_date = parse_date_only(field_value)
        expected_date = parse_date_only(expected_value)

        if actual_date is None or expected_date is None:
            return False

        if operator == "equals":
            return actual_date == expected_date
        if operator == "not_equals":
            return actual_date != expected_date
        if operator == "on_or_after":
            return actual_date >= expected_date
        if operator == "on_or_before":
            return actual_date <= expected_date

    return False


def evaluate_filter_rule(target: dict, rule: dict) -> bool:
    field_type = FIELD_TYPES[(rule["scope"], rule["field"])]
    field_value = get_field_value(target, rule["field"])

    return apply_operator(
        field_value=field_value,
        operator=rule["operator"],
        expected_value=rule["value"],
        field_type=field_type,
    )


def split_filters(filters: list[dict]):
    include_filters = [f for f in filters if f["mode"] == "include"]
    exclude_filters = [f for f in filters if f["mode"] == "exclude"]
    return include_filters, exclude_filters


def match_rules(rules: list[dict], evaluator, match_mode: str) -> bool:
    if not rules:
        return True

    results = [evaluator(rule) for rule in rules]

    if match_mode == "all":
        return all(results)

    if match_mode == "any":
        return any(results)

    raise ValueError('match_mode должен быть "all" или "any"')


def message_in_date_range(message: dict, date_from: str, date_to: str) -> bool:
    msg_date = parse_date_only(message.get("date"))
    if msg_date is None:
        return False

    from_date = parse_date_only(date_from) if date_from else None
    to_date = parse_date_only(date_to) if date_to else None

    if from_date and msg_date < from_date:
        return False

    if to_date and msg_date > to_date:
        return False

    return True


def filter_messages_in_chat(chat: dict, config: dict) -> list[dict]:
    """
    Возвращает список raw messages, которые подходят под message-фильтры и дату.
    """
    messages = chat.get("messages", [])
    if not isinstance(messages, list):
        return []

    include_filters, exclude_filters = split_filters(config["filters"])

    message_include_filters = [f for f in include_filters if f["scope"] == "message"]
    message_exclude_filters = [f for f in exclude_filters if f["scope"] == "message"]

    result_messages = []

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        # date range
        if config.get("date_from") or config.get("date_to"):
            if not message_in_date_range(msg, config.get("date_from", ""), config.get("date_to", "")):
                continue

        def eval_msg(rule):
            return evaluate_filter_rule(msg, rule)

        include_ok = match_rules(message_include_filters, eval_msg, config["match_mode"])
        exclude_ok = not any(eval_msg(rule) for rule in message_exclude_filters)

        if include_ok and exclude_ok:
            result_messages.append(msg)

    return result_messages


def chat_matches_advanced(chat: dict, config: dict) -> bool:
    include_filters, exclude_filters = split_filters(config["filters"])

    chat_include_filters = [f for f in include_filters if f["scope"] == "chat"]
    chat_exclude_filters = [f for f in exclude_filters if f["scope"] == "chat"]

    def eval_chat(rule):
        return evaluate_filter_rule(chat, rule)

    chat_include_ok = match_rules(chat_include_filters, eval_chat, config["match_mode"])
    chat_excluded = any(eval_chat(rule) for rule in chat_exclude_filters)

    if not chat_include_ok or chat_excluded:
        return False

    # message-фильтры тоже должны отработать, если они есть
    include_message_filters = [f for f in include_filters if f["scope"] == "message"]
    exclude_message_filters = [f for f in exclude_filters if f["scope"] == "message"]

    has_message_logic = bool(include_message_filters or exclude_message_filters or config.get("date_from") or config.get("date_to"))

    if not has_message_logic:
        return True

    matched_messages = filter_messages_in_chat(chat, config)
    return len(matched_messages) > 0


def build_output_chat(chat: dict, config: dict) -> dict | None:
    if config["output_mode"] == "full_chats":
        cleaned_messages = []
        for msg in chat.get("messages", []):
            cleaned = clean_message(msg)
            if cleaned is not None:
                cleaned_messages.append(cleaned)

        return {
            "id": chat.get("id"),
            "name": chat.get("name"),
            "messages": cleaned_messages,
        }

    if config["output_mode"] == "matched_messages_only":
        matched_raw_messages = filter_messages_in_chat(chat, config)
        cleaned_messages = []

        for msg in matched_raw_messages:
            cleaned = clean_message(msg)
            if cleaned is not None:
                cleaned_messages.append(cleaned)

        if not cleaned_messages:
            return None

        return {
            "id": chat.get("id"),
            "name": chat.get("name"),
            "messages": cleaned_messages,
        }

    raise ValueError("Неизвестный output_mode")


def apply_advanced_filters(data: dict, config: dict):
    config = normalize_advanced_config(config)
    profile_id = build_advanced_profile_id(config)

    if not isinstance(data, dict):
        raise ValueError("Корень JSON должен быть объектом.")

    chats_obj = data.get("chats")
    if not isinstance(chats_obj, dict):
        raise ValueError('Не найден объект "chats".')

    chat_list = chats_obj.get("list")
    if not isinstance(chat_list, list):
        raise ValueError('Не найден список "chats.list".')

    total_chats = len(chat_list)
    kept_raw_chats = []
    excluded_chats = []

    for chat in chat_list:
        if chat_matches_advanced(chat, config):
            kept_raw_chats.append(chat)
        else:
            excluded_chats.append({
                "id": chat.get("id"),
                "name": chat.get("name"),
                "type": chat.get("type"),
            })

    cleaned_chats = []

    for chat in kept_raw_chats:
        output_chat = build_output_chat(chat, config)
        if output_chat is not None:
            cleaned_chats.append(output_chat)

    result = {
        "mode": "advanced",
        "profile_id": profile_id,
        "chats": cleaned_chats,
    }

    stats = {
        "profile_id": profile_id,
        "total_chats": total_chats,
        "kept_after_filter": len(kept_raw_chats),
        "excluded_after_filter": len(excluded_chats),
        "final_chats_in_output": len(cleaned_chats),
        "match_mode": config["match_mode"],
        "output_mode": config["output_mode"],
        "date_from": config["date_from"],
        "date_to": config["date_to"],
        "filters_count": len(config["filters"]),
    }

    return result, stats, excluded_chats