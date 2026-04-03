from pathlib import Path
from datetime import datetime
import json


BASE_DIR = Path(__file__).resolve().parent
STATE_DIR = BASE_DIR / "state"
OUTPUT_DIR = BASE_DIR / "output"

STATE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_basic_profile_id() -> str:
    return "basic_default"


def get_profile_paths(mode: str, profile_id: str | None = None) -> dict:
    """
    Возвращает набор путей для state/output текущего профиля.

    mode:
      - "basic"
      - "advanced"

    profile_id:
      - для basic можно не передавать
      - для advanced обязателен
    """
    mode = str(mode or "").strip().lower()

    if mode not in {"basic", "advanced"}:
        raise ValueError('mode должен быть "basic" или "advanced"')

    if mode == "basic":
        resolved_profile_id = get_basic_profile_id()
        state_profile_dir = STATE_DIR / "basic" / resolved_profile_id
        output_mode_dir = OUTPUT_DIR / "basic"
    else:
        if not profile_id:
            raise ValueError("Для advanced mode нужен profile_id")
        resolved_profile_id = profile_id
        state_profile_dir = STATE_DIR / "advanced" / resolved_profile_id
        output_mode_dir = OUTPUT_DIR / "advanced" / resolved_profile_id

    state_profile_dir.mkdir(parents=True, exist_ok=True)
    output_mode_dir.mkdir(parents=True, exist_ok=True)

    return {
        "mode": mode,
        "profile_id": resolved_profile_id,
        "state_dir": state_profile_dir,
        "output_dir": output_mode_dir,
        "previous_total_path": state_profile_dir / "previous_total_filtered.json",
        "previous_meta_path": state_profile_dir / "previous_total_meta.json",
    }


def _load_json_if_exists(path: Path):
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_previous_total_for_profile(mode: str, profile_id: str | None = None):
    paths = get_profile_paths(mode, profile_id)
    return _load_json_if_exists(paths["previous_total_path"])


def load_previous_meta_for_profile(mode: str, profile_id: str | None = None):
    paths = get_profile_paths(mode, profile_id)
    return _load_json_if_exists(paths["previous_meta_path"])


def save_previous_total_for_profile(
    mode: str,
    profile_id: str | None,
    total_data: dict,
    meta: dict | None = None,
):
    paths = get_profile_paths(mode, profile_id)

    _save_json(paths["previous_total_path"], total_data)

    meta_payload = {
        "mode": paths["mode"],
        "profile_id": paths["profile_id"],
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "total_chats": len(total_data.get("chats", [])),
    }

    if meta:
        meta_payload.update(meta)

    _save_json(paths["previous_meta_path"], meta_payload)


def reset_profile_state(mode: str, profile_id: str | None = None):
    paths = get_profile_paths(mode, profile_id)

    if paths["previous_total_path"].exists():
        paths["previous_total_path"].unlink()

    if paths["previous_meta_path"].exists():
        paths["previous_meta_path"].unlink()