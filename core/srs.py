# Файл: core/srs.py
from datetime import datetime, timedelta, timezone

def calculate_next_due_date(repetitions: int, interval: float, ease_factor: float, quality: str) -> dict:
    if quality == 'again':
        repetitions = 0; interval = 1.0
    else:
        repetitions += 1
        if repetitions == 1: interval = 1.0
        elif repetitions == 2: interval = 6.0
        else: interval *= ease_factor
    ease_factor += (0.1 - (5 - {'again': 1, 'good': 3, 'easy': 5}[quality]) * (0.08 + (5 - {'again': 1, 'good': 3, 'easy': 5}[quality]) * 0.02))
    if ease_factor < 1.3: 
        ease_factor = 1.3
    due_date = datetime.now(timezone.utc) + timedelta(days=int(round(interval)))
    return {'repetitions': repetitions, 'interval': interval, 'ease_factor': ease_factor, 'due_date': due_date.strftime('%Y-%m-%dT%H:%M:%SZ')}