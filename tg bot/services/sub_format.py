from datetime import datetime

from database import Subscription


def subscription_period_text(sub: Subscription) -> str:
    if sub.is_permanent:
        return "♾️ Бессрочно (пока не удалите)"
    if not sub.expires_at:
        return "—"
    dt = datetime.fromtimestamp(sub.expires_at).strftime("%d.%m.%Y %H:%M")
    if sub.is_active:
        return f"⏱ До {dt}"
    return f"⌛ Истекла {dt}"
