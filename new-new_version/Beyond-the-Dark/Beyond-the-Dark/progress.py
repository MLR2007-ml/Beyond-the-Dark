# progress.py
"""Сохранение прогресса: лучшие монеты и звёзды по уровням."""
import json

import settings

_cache = None


def load():
    """Читает save.json один раз и держит данные в памяти."""
    global _cache
    if _cache is not None:
        return _cache

    data = {"levels": {}}
    try:
        with open(settings.SAVE_FILE, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if isinstance(raw, dict):
            data = raw
            if not isinstance(data.get("levels"), dict):
                data["levels"] = {}
    except (OSError, ValueError):
        data = {"levels": {}}

    _cache = data
    return _cache


def flush():
    if _cache is None:
        return
    try:
        with open(settings.SAVE_FILE, "w", encoding="utf-8") as handle:
            json.dump(_cache, handle, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[ПРЕДУПРЕЖДЕНИЕ] Прогресс не сохранён: {exc}")


def stars_for(collected, total):
    """50% монет — 1 звезда, 80% — 2, 100% — 3."""
    if total <= 0:
        return 3
    ratio = collected / total
    if ratio >= 1.0:
        return 3
    if ratio >= settings.STAR_THRESHOLDS[1]:
        return 2
    if ratio >= settings.STAR_THRESHOLDS[0]:
        return 1
    return 0


def record(level, collected, total):
    """Записывает результат забега и возвращает полученные звёзды."""
    entry = load()["levels"].setdefault(
        str(level), {"coins": 0, "total": total, "stars": 0})
    entry["total"] = total
    entry["coins"] = max(entry.get("coins", 0), collected)
    stars = stars_for(collected, total)
    entry["stars"] = max(entry.get("stars", 0), stars)
    flush()
    return stars


def level_info(level):
    """(лучшие монеты, звёзды) для карточки выбора уровня."""
    entry = load()["levels"].get(str(level), {})
    return entry.get("coins", 0), entry.get("stars", 0)


def audio_volumes():
    """Сохранённые громкости музыки и звуков (None — значения по умолчанию)."""
    data = load().get("audio")
    if not isinstance(data, dict):
        return None, None

    result = []
    for key in ("music", "sfx"):
        value = data.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            result.append(max(0.0, min(1.0, float(value))))
        else:
            result.append(None)
    return result[0], result[1]


def save_audio_volumes(music, sfx):
    """Запоминает громкости, чтобы ползунки стояли на месте после перезапуска."""
    load()["audio"] = {"music": round(float(music), 2), "sfx": round(float(sfx), 2)}
    flush()


def total_stars():
    return sum(entry.get("stars", 0) for entry in load()["levels"].values())
