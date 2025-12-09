from datetime import datetime, timedelta
from typing import Optional

import pytz

IST = pytz.timezone("Asia/Kolkata")


def now_ist_iso() -> str:
    return datetime.now(IST).isoformat()


def utc_iso() -> str:
    return datetime.utcnow().isoformat()


def schedule_in_hours_ist(hours: int) -> str:
    return (datetime.now(IST) + timedelta(hours=hours)).isoformat()

