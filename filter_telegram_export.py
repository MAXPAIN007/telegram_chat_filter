from pathlib import Path
import json

# =========================================================
# НАСТРОЙКИ
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

# True  -> обработать все result*.json из папки input
# False -> обработать только один файл INPUT_FILENAME
PROCESS_ALL_FILES = True

# Используется только если PROCESS_ALL_FILES = False
# ЗДЕСЬ можно вручную менять имя файла
INPUT_FILENAME = "result1.json"

# result1.json -> result1_filtered_clean.json
OUTPUT_SUFFIX = "_filtered_clean"

# Режим фильтрации:
# "exclude" -> если найдено ключевое слово, чат ИСКЛЮЧАЕМ
# "include" -> если найдено ключевое слово, чат ВКЛЮЧАЕМ
FILTER_MODE = "include"

# Если надо учитывать только personal_chat
ONLY_PERSONAL_CHATS = False

# Ключевые слова
# Поиск без учёта регистра
KEYWORDS = [
    "client",
    "клиент",
]

# Дополнительная проверка по полю FROM
CHECK_FIRST_MESSAGES_FROM = True
FIRST_MESSAGES_LIMIT = 10

# Если после чистки в чате не осталось сообщений — удалять ли чат
DROP_CHATS_WITHOUT_MESSAGES = False


# =========================================================
# НОРМАЛИЗАЦИЯ
# =========================================================

def norm(value):
    return str(value or "").strip().casefold()


KEYWORDS_NORM = [norm(x) for x in KEYWORDS if norm(x)]


# =========================================================
# РАБОТА С ФАЙЛАМИ
# =========================================================

def get_input_files():
    if PROCESS_ALL_FILES:
        files = sorted(INPUT_DIR.glob("result*.json"))
        if not files:
            raise FileNotFoundError(
                f'В папке "{INPUT_DIR}" не найдены файлы вида result*.json'
            )
        return files

    path = INPUT_DIR / INPUT_FILENAME
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    return [path]


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# =========================================================
# ФИЛЬТРАЦИЯ ЧАТОВ
# =========================================================

def is_personal_chat(chat: dict) -> bool:
    return norm(chat.get("type")) == "personal_chat"


def contains_keywords(text: str) -> bool:
    text_norm = norm(text)
    return any(keyword in text_norm for keyword in KEYWORDS_NORM)


def chat_name_matches(chat: dict) -> bool:
    return contains_keywords(chat.get("name", ""))


def first_messages_from_matches(chat: dict) -> bool:
    """
    Проверяем поле FROM в первых N сообщениях.
    Если хотя бы в одном есть ключевое слово -> True
    """
    if not CHECK_FIRST_MESSAGES_FROM:
        return False

    messages = chat.get("messages", [])
    if not isinstance(messages, list):
        return False

    checked = 0

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        sender = msg.get("from", "")
        if contains_keywords(sender):
            return True

        checked += 1
        if checked >= FIRST_MESSAGES_LIMIT:
            break

    return False


def should_keep_chat(chat: dict) -> bool:
    if not isinstance(chat, dict):
        return False

    if ONLY_PERSONAL_CHATS and not is_personal_chat(chat):
        return False

    matched_in_name = chat_name_matches(chat)
    matched_in_from = first_messages_from_matches(chat)

    matched = matched_in_name or matched_in_from

    if FILTER_MODE == "exclude":
        return not matched

    if FILTER_MODE == "include":
        return matched

    raise ValueError('FILTER_MODE должен быть "exclude" или "include"')


# =========================================================
# ЧИСТКА СООБЩЕНИЙ
# =========================================================

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
    """
    Оставляем только:
    - id
    - reply_to_message_id (если есть)
    - date
    - from
    - text
    """
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


def clean_chat(chat: dict):
    cleaned_messages = []

    for msg in chat.get("messages", []):
        cleaned_msg = clean_message(msg)
        if cleaned_msg is not None:
            cleaned_messages.append(cleaned_msg)

    if DROP_CHATS_WITHOUT_MESSAGES and not cleaned_messages:
        return None

    return {
        "id": chat.get("id"),
        "name": chat.get("name"),
        "messages": cleaned_messages,
    }


# =========================================================
# ОСНОВНАЯ ЛОГИКА
# =========================================================

def filter_and_clean_export(data: dict):
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
        if should_keep_chat(chat):
            kept_raw_chats.append(chat)
        else:
            excluded_chats.append({
                "id": chat.get("id"),
                "name": chat.get("name"),
                "type": chat.get("type"),
            })

    cleaned_chats = []
    for chat in kept_raw_chats:
        cleaned_chat = clean_chat(chat)
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
        "filter_mode": FILTER_MODE,
        "keywords": KEYWORDS,
        "only_personal_chats": ONLY_PERSONAL_CHATS,
        "check_first_messages_from": CHECK_FIRST_MESSAGES_FROM,
        "first_messages_limit": FIRST_MESSAGES_LIMIT,
        "drop_chats_without_messages": DROP_CHATS_WITHOUT_MESSAGES,
    }

    return result, stats, excluded_chats


def process_file(input_path: Path):
    print(f"\nЧитаю: {input_path.name}")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned_data, stats, excluded_chats = filter_and_clean_export(data)

    output_filename = f"{input_path.stem}{OUTPUT_SUFFIX}.json"
    report_filename = f"{input_path.stem}{OUTPUT_SUFFIX}_report.json"

    output_path = OUTPUT_DIR / output_filename
    report_path = OUTPUT_DIR / report_filename

    save_json(output_path, cleaned_data)
    save_json(report_path, {
        "source_file": input_path.name,
        "stats": stats,
        "excluded_chats_preview": excluded_chats[:5000]
    })

    print(f"Готово: {output_path.name}")
    print(
        f"Всего чатов: {stats['total_chats']} | "
        f"Оставлено после фильтра: {stats['kept_after_filter']} | "
        f"Исключено: {stats['excluded_after_filter']} | "
        f"Финально в output: {stats['final_chats_in_output']}"
    )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = get_input_files()
    print(f"Найдено файлов для обработки: {len(files)}")

    for input_path in files:
        try:
            process_file(input_path)
        except Exception as e:
            print(f"Ошибка при обработке {input_path.name}: {e}")

    print("\nОбработка завершена.")


if __name__ == "__main__":
    main()