import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    import re
    text = str(text or '').strip().lower()
    # Remove accents
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('ascii')
    # Replace non-alphanumeric with hyphen
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def format_currency(value: float, currency: str = "R$") -> str:
    """Format currency for Brazilian Portuguese"""
    if value is None:
        value = 0
    return f"{currency} {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def time_ago(date: Optional[datetime]) -> str:
    """Return human-readable time ago"""
    if not date:
        return '—'
    
    if isinstance(date, str):
        date = datetime.fromisoformat(date.replace('Z', '+00:00'))
    
    now = datetime.now(date.tzinfo) if date.tzinfo else datetime.now()
    diff = now - date
    seconds = int(diff.total_seconds())
    
    if seconds < 0:
        return 'agora'
    if seconds < 60:
        return 'agora'
    
    minutes = seconds // 60
    if minutes < 60:
        return f'{minutes}min'
    
    hours = minutes // 60
    if hours < 24:
        return f'{hours}h {minutes % 60}min'
    
    days = hours // 24
    return f'{days}d'


def today_iso() -> datetime:
    """Return today as datetime object with UTC timezone"""
    return datetime.now(timezone.utc)


def is_today(date: datetime) -> bool:
    """Check if date is today"""
    now = datetime.now()
    return date.date() == now.date()


def day_key(date: datetime) -> str:
    """Return day key as DD/MM"""
    return f"{date.day:02d}/{date.month:02d}"