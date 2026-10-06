import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


USAGE_FILE = Path("usage.json")
KABUL_TIMEZONE = ZoneInfo("Asia/Kabul")
_USAGE_LOCK = threading.Lock()


def _value(source, name):
    if isinstance(source, dict):
        return source.get(name)
    return getattr(source, name, None)


def _token_count(value):
    return value if isinstance(value, int) and value >= 0 else 0


def _read_records():
    try:
        records = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return records if isinstance(records, list) else []


def record_response_usage(response):
    """Persist token counts reported by a completed DeepSeek response."""
    usage = _value(response, "usage")
    if usage is None:
        return

    input_tokens = _token_count(
        _value(usage, "prompt_tokens") or _value(usage, "input_tokens")
    )
    output_tokens = _token_count(
        _value(usage, "completion_tokens") or _value(usage, "output_tokens")
    )
    total_tokens = _token_count(_value(usage, "total_tokens"))
    if not total_tokens:
        total_tokens = input_tokens + output_tokens

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cache_hit_tokens": _token_count(
            _value(usage, "prompt_cache_hit_tokens")
            or _value(usage, "cache_hit_tokens")
        ),
        "cache_miss_tokens": _token_count(
            _value(usage, "prompt_cache_miss_tokens")
            or _value(usage, "cache_miss_tokens")
        ),
    }

    with _USAGE_LOCK:
        records = _read_records()
        records.append(record)
        temporary_file = USAGE_FILE.with_name(f"{USAGE_FILE.name}.tmp")
        temporary_file.write_text(
            json.dumps(records, indent=2) + "\n", encoding="utf-8"
        )
        temporary_file.replace(USAGE_FILE)


def _timezone(timezone_name):
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return datetime.now().astimezone().tzinfo or timezone.utc


def summarize_usage(timezone_name="UTC", now=None):
    """Summarize persisted usage for the current local calendar month."""
    local_timezone = _timezone(timezone_name)
    current_time = (now or datetime.now(timezone.utc)).astimezone(local_timezone)
    kabul_time = (now or datetime.now(timezone.utc)).astimezone(KABUL_TIMEZONE)
    month_total = 0

    for record in _read_records():
        if not isinstance(record, dict):
            continue
        try:
            timestamp = datetime.fromisoformat(record["timestamp"])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            local_timestamp = timestamp.astimezone(local_timezone)
        except (KeyError, TypeError, ValueError):
            continue
        if (local_timestamp.year, local_timestamp.month) == (
            current_time.year,
            current_time.month,
        ):
            month_total += _token_count(record.get("total_tokens"))

    day_count = current_time.day
    minute_of_day = kabul_time.hour * 60 + kabul_time.minute
    is_weekday = kabul_time.weekday() < 5
    is_peak = is_weekday and (
        5 * 60 + 30 <= minute_of_day < 8 * 60 + 30
        or 10 * 60 + 30 <= minute_of_day < 14 * 60 + 30
    )
    return {
        "month_tokens": month_total,
        "daily_average_tokens": month_total / day_count,
        "days_elapsed": day_count,
        "monthly_warning": month_total >= 1_000_000,
        "local_time": kabul_time.strftime("%I:%M %p").lstrip("0"),
        "peak": is_peak,
        "peak_status": "Peak" if is_peak else "Off-peak",
    }