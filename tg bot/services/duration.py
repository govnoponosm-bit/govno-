from __future__ import annotations

import re
import time
from datetime import datetime


def parse_duration_to_expires_at(text: str) -> int | None:
    """
    Возвращает Unix-время окончания подписки или None, если не распознано.
    Примеры: 1ч, 24ч, 7д, 30д, 1h, 7d, 01.06.2026 18:00, 01.06.2026
    """
    text = text.strip().lower().replace(",", ".")
    if not text:
        return None

    now = int(time.time())

    m = re.fullmatch(r"(\d+)\s*(ч|h|час|часа|часов)", text)
    if m:
        return now + int(m.group(1)) * 3600

    m = re.fullmatch(r"(\d+)\s*(д|d|день|дня|дней|сут|суток)", text)
    if m:
        return now + int(m.group(1)) * 86400

    m = re.fullmatch(r"(\d+)\s*(м|min|мин|минут|минуты)", text)
    if m:
        return now + int(m.group(1)) * 60

    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            ts = int(dt.timestamp())
            if ts <= now:
                return None
            return ts
        except ValueError:
            continue

    return None
