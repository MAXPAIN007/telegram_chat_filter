from pathlib import Path
from datetime import datetime
import os
import mimetypes
import requests

from flask import Flask, render_template, request, send_from_directory, url_for, redirect, jsonify
from werkzeug.utils import secure_filename

from defaults import (
    DEFAULT_FILTER_MODE,
    DEFAULT_KEYWORDS,
    DEFAULT_ONLY_PERSONAL_CHATS,
    DEFAULT_CHECK_FIRST_MESSAGES_FROM,
    DEFAULT_FIRST_MESSAGES_LIMIT,
    DEFAULT_DROP_CHATS_WITHOUT_MESSAGES,
)
from parser_core import (
    load_json_file,
    save_json_file,
    filter_and_clean_export,
)
from delta_core import (
    merge_filtered_results,
    load_json_if_exists,
    compute_delta,
)

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
STATE_DIR = BASE_DIR / "state"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

PREVIOUS_TOTAL_PATH = STATE_DIR / "previous_total_filtered.json"
PREVIOUS_TOTAL_META_PATH = STATE_DIR / "previous_total_meta.json"

app = Flask(__name__)

SUPPORTED_LANGS = {"ru", "en"}
DEFAULT_LANG = "ru"

TRANSLATIONS = {
    "ru": {
        "app_title": "Telegram Chat Filter",
        "hero_title": "Telegram Chat Filter",
        "intro": "Локальный инструмент для фильтрации Telegram export JSON, очистки сообщений, сборки полного файла и вычисления обновлений.",
        "local_only": "Только локально",
        "raw_telegram_export": "Raw Telegram export JSON",
        "raw_export_help": "Можно загрузить один или несколько JSON-файлов сразу.",
        "choose_files": "Выбрать файлы",
        "no_files_selected": "Файлы не выбраны",
        "files_selected_template": "Выбрано файлов: {count}",
        "filter_mode": "Режим фильтрации",
        "mode_include": "Include — оставить чаты, где найдено ключевое слово",
        "mode_exclude": "Exclude — исключить чаты, где найдено ключевое слово",
        "keywords": "Ключевые слова",
        "keywords_help": "Можно вводить через запятую, точку с запятой или с новой строки. Если поле пустое, используются значения из defaults.py.",
        "run_processing": "Запустить обработку",
        "current_delta_state": "Текущее состояние delta",
        "previous_total_found": "Previous total",
        "found": "найден",
        "not_found": "не найден",
        "run_id": "Run ID",
        "saved_at": "Сохранён",
        "chats": "Чатов",
        "next_run_first_delta": "Следующий запуск будет считаться первым для delta.",
        "reset_delta_history": "Сбросить историю delta",
        "reset_success": "История delta/state сброшена.",
        "agent_sending": "Отправка агенту",
        "enabled": "включена",
        "disabled": "выключена",
        "max_file_size": "Макс. размер файла",
        "auth_header": "Auth header",
        "result": "Результат",
        "input_files": "Входных файлов",
        "processed": "Успешно обработано",
        "failed": "С ошибками",
        "input_chats": "Всего чатов во входных файлах",
        "kept_after_filter": "Оставлено после фильтра",
        "excluded_after_filter": "Исключено после фильтра",
        "final_after_cleaning": "Финально после чистки",
        "total_chats": "Чатов в total",
        "delta_summary": "Delta summary",
        "previous_total_chats": "Чатов в предыдущем total",
        "current_total_chats": "Чатов в текущем total",
        "delta_chats": "Чатов в delta",
        "delta_full_chats": "Чатов в delta-full",
        "new_chats": "Новых чатов",
        "updated_existing_chats": "Обновлённых существующих чатов",
        "new_messages_in_delta": "Новых сообщений в delta",
        "first_run": "Первый запуск",
        "yes": "Да",
        "no": "Нет",
        "output_files": "Выходные файлы",
        "total_filtered_desc": "Полный текущий отфильтрованный срез по всем загруженным файлам.",
        "delta_updates_desc": "Только новые сообщения и новые чаты относительно предыдущего total.",
        "delta_full_desc": "Полные версии только тех чатов, которые обновились или появились впервые.",
        "download": "Скачать",
        "send_to_agent": "Отправить агенту",
        "files_by_source": "Файлы по каждому источнику",
        "filtered_json": "Filtered JSON",
        "report_json": "Report JSON",
        "processing_report": "Общий отчёт",
        "error_invalid_filter_mode": 'filter_mode должен быть "include" или "exclude"',
        "error_no_files": "Загрузи хотя бы один JSON-файл.",
        "agent_not_configured": "Webhook агента не настроен. Добавьте AGENT_WEBHOOK_URL в .env",
        "file_not_found": "Файл не найден: {filename}",
        "file_too_large": 'Файл "{filename}" слишком большой ({size_mb:.2f} MB). Текущий лимит: {limit_mb:.2f} MB.',
        "agent_http_error": "Webhook вернул HTTP {status}. {details}",
        "send_success_template": 'Файл "{filename}" успешно отправлен. HTTP {status}. Размер: {size} MB.',
        "send_error_fallback": "Не удалось отправить файл агенту.",
        "reset_modal_title": "Сбросить историю delta?",
        "reset_modal_text": "После сброса следующий запуск будет считаться первым. Сравнение с предыдущим total больше не выполнится, а файл обновлений будет построен заново.",
        "cancel": "Отмена",
        "confirm": "Подтвердить",
        "close": "Закрыть",
        "language": "Язык",
    },
    "en": {
        "app_title": "Telegram Chat Filter",
        "hero_title": "Telegram Chat Filter",
        "intro": "Local tool for filtering Telegram export JSON, cleaning messages, building a full snapshot, and calculating updates.",
        "local_only": "Local only",
        "raw_telegram_export": "Raw Telegram export JSON",
        "raw_export_help": "You can upload one or multiple JSON files at once.",
        "choose_files": "Choose files",
        "no_files_selected": "No files selected",
        "files_selected_template": "Selected files: {count}",
        "filter_mode": "Filter mode",
        "mode_include": "Include — keep chats where a keyword is found",
        "mode_exclude": "Exclude — remove chats where a keyword is found",
        "keywords": "Keywords",
        "keywords_help": "You can use commas, semicolons, or new lines. If empty, defaults from defaults.py will be used.",
        "run_processing": "Run processing",
        "current_delta_state": "Current delta state",
        "previous_total_found": "Previous total",
        "found": "found",
        "not_found": "not found",
        "run_id": "Run ID",
        "saved_at": "Saved at",
        "chats": "Chats",
        "next_run_first_delta": "The next run will be treated as the first delta run.",
        "reset_delta_history": "Reset delta history",
        "reset_success": "Delta/state history has been reset.",
        "agent_sending": "Agent sending",
        "enabled": "enabled",
        "disabled": "disabled",
        "max_file_size": "Max file size",
        "auth_header": "Auth header",
        "result": "Result",
        "input_files": "Input files",
        "processed": "Processed successfully",
        "failed": "Failed",
        "input_chats": "Total chats in input files",
        "kept_after_filter": "Kept after filter",
        "excluded_after_filter": "Excluded after filter",
        "final_after_cleaning": "Final after cleaning",
        "total_chats": "Chats in total",
        "delta_summary": "Delta summary",
        "previous_total_chats": "Chats in previous total",
        "current_total_chats": "Chats in current total",
        "delta_chats": "Chats in delta",
        "delta_full_chats": "Chats in delta-full",
        "new_chats": "New chats",
        "updated_existing_chats": "Updated existing chats",
        "new_messages_in_delta": "New messages in delta",
        "first_run": "First run",
        "yes": "Yes",
        "no": "No",
        "output_files": "Output files",
        "total_filtered_desc": "Full current filtered snapshot across all uploaded files.",
        "delta_updates_desc": "Only new messages and new chats compared to the previous total.",
        "delta_full_desc": "Full versions of chats that were updated or appeared for the first time.",
        "download": "Download",
        "send_to_agent": "Send to agent",
        "files_by_source": "Files by source",
        "filtered_json": "Filtered JSON",
        "report_json": "Report JSON",
        "processing_report": "Processing report",
        "error_invalid_filter_mode": 'filter_mode must be "include" or "exclude"',
        "error_no_files": "Upload at least one JSON file.",
        "agent_not_configured": "Agent webhook is not configured. Add AGENT_WEBHOOK_URL to .env",
        "file_not_found": "File not found: {filename}",
        "file_too_large": 'File "{filename}" is too large ({size_mb:.2f} MB). Current limit: {limit_mb:.2f} MB.',
        "agent_http_error": "Webhook returned HTTP {status}. {details}",
        "send_success_template": 'File "{filename}" sent successfully. HTTP {status}. Size: {size} MB.',
        "send_error_fallback": "Failed to send file to agent.",
        "reset_modal_title": "Reset delta history?",
        "reset_modal_text": "After reset, the next run will be treated as the first one. Comparison with the previous total will no longer be available, and the updates file will be built from scratch.",
        "cancel": "Cancel",
        "confirm": "Confirm",
        "close": "Close",
        "language": "Language",
    },
}


def resolve_lang(raw_lang: str | None) -> str:
    lang = (raw_lang or "").strip().lower()
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def tr(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG]).get(key, key)


def load_env_file(env_path: Path):
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file(BASE_DIR / ".env")

AGENT_WEBHOOK_URL = os.getenv("AGENT_WEBHOOK_URL", "").strip()
AGENT_AUTH_HEADER_NAME = os.getenv("AGENT_AUTH_HEADER_NAME", "").strip()
AGENT_AUTH_HEADER_VALUE = os.getenv("AGENT_AUTH_HEADER_VALUE", "").strip()
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "60"))
AGENT_MAX_FILE_SIZE_MB = float(os.getenv("AGENT_MAX_FILE_SIZE_MB", "16"))


def parse_keywords(raw_value: str) -> list[str]:
    if not raw_value or not raw_value.strip():
        return []

    normalized = raw_value.replace(";", ",")
    parts = []

    for line in normalized.splitlines():
        for chunk in line.split(","):
            value = chunk.strip()
            if value:
                parts.append(value)

    return parts


def build_safe_stem(filename: str, index: int) -> str:
    original_stem = Path(filename).stem
    safe_stem = secure_filename(original_stem)
    return safe_stem or f"file_{index}"


def get_previous_state_info():
    if not PREVIOUS_TOTAL_PATH.exists():
        return {
            "exists": False,
            "run_id": None,
            "saved_at": None,
            "total_chats": 0,
        }

    meta = load_json_if_exists(PREVIOUS_TOTAL_META_PATH) or {}
    total_chats = meta.get("total_chats")

    if total_chats is None:
        previous_total = load_json_if_exists(PREVIOUS_TOTAL_PATH) or {"chats": []}
        total_chats = len(previous_total.get("chats", []))

    return {
        "exists": True,
        "run_id": meta.get("run_id"),
        "saved_at": meta.get("saved_at"),
        "total_chats": total_chats,
    }


def save_previous_state_meta(run_id: str, total_chats: int):
    save_json_file(PREVIOUS_TOTAL_META_PATH, {
        "run_id": run_id,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "total_chats": total_chats,
    })


def get_agent_info():
    return {
        "configured": bool(AGENT_WEBHOOK_URL),
        "max_file_size_mb": AGENT_MAX_FILE_SIZE_MB,
        "auth_enabled": bool(AGENT_AUTH_HEADER_NAME and AGENT_AUTH_HEADER_VALUE),
    }


def get_file_size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def send_output_file_to_agent(run_id: str, filename: str, lang: str):
    if not AGENT_WEBHOOK_URL:
        raise ValueError(tr(lang, "agent_not_configured"))

    file_path = OUTPUT_DIR / run_id / filename
    if not file_path.exists():
        raise FileNotFoundError(tr(lang, "file_not_found").format(filename=filename))

    size_mb = get_file_size_mb(file_path)
    if size_mb > AGENT_MAX_FILE_SIZE_MB:
        raise ValueError(
            tr(lang, "file_too_large").format(
                filename=filename,
                size_mb=size_mb,
                limit_mb=AGENT_MAX_FILE_SIZE_MB,
            )
        )

    headers = {}
    if AGENT_AUTH_HEADER_NAME and AGENT_AUTH_HEADER_VALUE:
        headers[AGENT_AUTH_HEADER_NAME] = AGENT_AUTH_HEADER_VALUE

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/json"

    with file_path.open("rb") as f:
        response = requests.post(
            AGENT_WEBHOOK_URL,
            headers=headers,
            data={
                "run_id": run_id,
                "filename": filename,
                "source": "telegram_chat_filter",
                "content_type": content_type,
            },
            files={
                "file": (file_path.name, f, content_type)
            },
            timeout=AGENT_TIMEOUT_SECONDS,
        )

    if not response.ok:
        text = response.text[:1000] if response.text else ""
        raise ValueError(
            tr(lang, "agent_http_error").format(
                status=response.status_code,
                details=text,
            )
        )

    return {
        "filename": filename,
        "size_mb": round(size_mb, 2),
        "status_code": response.status_code,
        "response_text": (response.text[:500] if response.text else ""),
    }


@app.route("/", methods=["GET", "POST"])
def index():
    lang = resolve_lang(request.values.get("lang"))
    tr_fn = lambda key: tr(lang, key)

    state_info = get_previous_state_info()
    agent_info = get_agent_info()

    result_context = {
        "error": None,
        "success": False,
        "downloads": [],
        "total_download": None,
        "delta_download": None,
        "delta_full_download": None,
        "report_download": None,
        "run_id": None,
        "form_values": {
            "filter_mode": DEFAULT_FILTER_MODE,
            "keywords": ", ".join(DEFAULT_KEYWORDS),
        },
        "summary": None,
        "delta_summary": None,
        "state_info": state_info,
        "agent_info": agent_info,
        "state_reset_done": request.args.get("reset") == "1",
        "lang": lang,
        "tr": tr_fn,
    }

    if request.method == "GET":
        return render_template("index.html", **result_context)

    uploaded_files = [
        file for file in request.files.getlist("files")
        if file and file.filename
    ]

    filter_mode = request.form.get("filter_mode", DEFAULT_FILTER_MODE).strip().lower()
    raw_keywords = request.form.get("keywords", "")
    parsed_keywords = parse_keywords(raw_keywords)
    keywords = parsed_keywords if parsed_keywords else DEFAULT_KEYWORDS

    result_context["form_values"] = {
        "filter_mode": filter_mode,
        "keywords": raw_keywords,
    }

    if filter_mode not in {"include", "exclude"}:
        result_context["error"] = tr_fn("error_invalid_filter_mode")
        return render_template("index.html", **result_context)

    if not uploaded_files:
        result_context["error"] = tr_fn("error_no_files")
        return render_template("index.html", **result_context)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_upload_dir = UPLOADS_DIR / run_id
    run_output_dir = OUTPUT_DIR / run_id

    run_upload_dir.mkdir(parents=True, exist_ok=True)
    run_output_dir.mkdir(parents=True, exist_ok=True)

    processed_outputs = []
    filtered_payloads = []
    file_reports = []

    total_input_files = len(uploaded_files)
    successfully_processed_files = 0

    total_input_chats = 0
    total_kept_after_filter = 0
    total_excluded_after_filter = 0
    total_final_chats_after_cleaning = 0

    for index, file in enumerate(uploaded_files, start=1):
        original_filename = file.filename
        safe_upload_name = secure_filename(original_filename) or f"upload_{index}.json"
        safe_stem = build_safe_stem(original_filename, index)

        upload_path = run_upload_dir / f"{index:03d}_{safe_upload_name}"
        file.save(upload_path)

        try:
            data = load_json_file(upload_path)

            cleaned_data, stats, excluded_chats = filter_and_clean_export(
                data=data,
                filter_mode=filter_mode,
                keywords=keywords,
                only_personal_chats=DEFAULT_ONLY_PERSONAL_CHATS,
                check_first_messages_from=DEFAULT_CHECK_FIRST_MESSAGES_FROM,
                first_messages_limit=DEFAULT_FIRST_MESSAGES_LIMIT,
                drop_chats_without_messages=DEFAULT_DROP_CHATS_WITHOUT_MESSAGES,
            )

            output_filename = f"{index:03d}_{safe_stem}_filtered_clean.json"
            report_filename = f"{index:03d}_{safe_stem}_report.json"

            output_path = run_output_dir / output_filename
            report_path = run_output_dir / report_filename

            save_json_file(output_path, cleaned_data)
            save_json_file(report_path, {
                "source_file": original_filename,
                "saved_upload_file": upload_path.name,
                "stats": stats,
                "excluded_chats_preview": excluded_chats[:5000],
            })

            filtered_payloads.append(cleaned_data)
            file_reports.append({
                "source_file": original_filename,
                "saved_upload_file": upload_path.name,
                "output_file": output_filename,
                "report_file": report_filename,
                "stats": stats,
            })

            processed_outputs.append({
                "source_file": original_filename,
                "output_file": output_filename,
                "report_file": report_filename,
                "output_download_url": url_for("download_file", run_id=run_id, filename=output_filename),
                "report_download_url": url_for("download_file", run_id=run_id, filename=report_filename),
                "stats": stats,
            })

            successfully_processed_files += 1
            total_input_chats += stats["total_chats"]
            total_kept_after_filter += stats["kept_after_filter"]
            total_excluded_after_filter += stats["excluded_after_filter"]
            total_final_chats_after_cleaning += stats["final_chats_in_output"]

        except Exception as e:
            file_reports.append({
                "source_file": original_filename,
                "saved_upload_file": upload_path.name,
                "error": str(e),
            })

    total_filename = "total_filtered.json"
    delta_filename = "delta_updates.json"
    delta_full_filename = "delta_full_chats.json"
    report_filename = "processing_report.json"

    total_data = merge_filtered_results(filtered_payloads) if filtered_payloads else {"chats": []}

    previous_total = load_json_if_exists(PREVIOUS_TOTAL_PATH)
    delta_data, delta_full_data, delta_stats = compute_delta(previous_total, total_data)

    total_path = run_output_dir / total_filename
    delta_path = run_output_dir / delta_filename
    delta_full_path = run_output_dir / delta_full_filename
    report_path = run_output_dir / report_filename

    save_json_file(total_path, total_data)
    save_json_file(delta_path, delta_data)
    save_json_file(delta_full_path, delta_full_data)
    save_json_file(PREVIOUS_TOTAL_PATH, total_data)
    save_previous_state_meta(run_id, len(total_data.get("chats", [])))

    processing_report = {
        "run_id": run_id,
        "settings": {
            "filter_mode": filter_mode,
            "keywords": keywords,
            "only_personal_chats": DEFAULT_ONLY_PERSONAL_CHATS,
            "check_first_messages_from": DEFAULT_CHECK_FIRST_MESSAGES_FROM,
            "first_messages_limit": DEFAULT_FIRST_MESSAGES_LIMIT,
            "drop_chats_without_messages": DEFAULT_DROP_CHATS_WITHOUT_MESSAGES,
        },
        "summary": {
            "total_input_files": total_input_files,
            "successfully_processed_files": successfully_processed_files,
            "failed_files": total_input_files - successfully_processed_files,
            "total_input_chats": total_input_chats,
            "total_kept_after_filter": total_kept_after_filter,
            "total_excluded_after_filter": total_excluded_after_filter,
            "total_final_chats_after_cleaning": total_final_chats_after_cleaning,
            "total_chats_in_total_output": len(total_data.get("chats", [])),
        },
        "delta_summary": delta_stats,
        "files": file_reports,
    }

    save_json_file(report_path, processing_report)

    result_context["success"] = True
    result_context["run_id"] = run_id
    result_context["downloads"] = processed_outputs
    result_context["total_download"] = {
        "filename": total_filename,
        "url": url_for("download_file", run_id=run_id, filename=total_filename),
    }
    result_context["delta_download"] = {
        "filename": delta_filename,
        "url": url_for("download_file", run_id=run_id, filename=delta_filename),
    }
    result_context["delta_full_download"] = {
        "filename": delta_full_filename,
        "url": url_for("download_file", run_id=run_id, filename=delta_full_filename),
    }
    result_context["report_download"] = {
        "filename": report_filename,
        "url": url_for("download_file", run_id=run_id, filename=report_filename),
    }
    result_context["summary"] = processing_report["summary"]
    result_context["delta_summary"] = processing_report["delta_summary"]
    result_context["state_info"] = get_previous_state_info()
    result_context["agent_info"] = get_agent_info()

    return render_template("index.html", **result_context)


@app.route("/reset-state", methods=["POST"])
def reset_state():
    lang = resolve_lang(request.form.get("lang") or request.args.get("lang"))

    if PREVIOUS_TOTAL_PATH.exists():
        PREVIOUS_TOTAL_PATH.unlink()

    if PREVIOUS_TOTAL_META_PATH.exists():
        PREVIOUS_TOTAL_META_PATH.unlink()

    return redirect(url_for("index", reset="1", lang=lang))


@app.route("/send-to-agent/<run_id>/<path:filename>", methods=["POST"])
def send_to_agent(run_id: str, filename: str):
    lang = resolve_lang(request.args.get("lang"))

    try:
        result = send_output_file_to_agent(run_id, filename, lang)
        return jsonify({
            "ok": True,
            "details": result,
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": str(e),
        }), 400


@app.route("/download/<run_id>/<path:filename>")
def download_file(run_id: str, filename: str):
    directory = OUTPUT_DIR / run_id
    return send_from_directory(directory, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)