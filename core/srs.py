# Файл: core/srs.py (НОВАЯ, ПОЛНАЯ ВЕРСИЯ)

from datetime import datetime, timedelta, timezone

def calculate_next_due_date(repetitions: int, interval: float, ease_factor: float, quality: str) -> dict:
    """
    Продвинутый SRS-алгоритм, основанный на SM-2.
    `quality` может быть 'again', 'good', 'easy'.
    """
    if quality == 'again':
        repetitions = 0
        interval = 1.0
    else:
        repetitions += 1
        if repetitions == 1:
            interval = 1.0
        elif repetitions == 2:
            interval = 6.0
        else:
            interval *= ease_factor

    # Обновляем фактор легкости
    ease_factor += (0.1 - (5 - {'again': 1, 'good': 3, 'easy': 5}[quality]) * (0.08 + (5 - {'again': 1, 'good': 3, 'easy': 5}[quality]) * 0.02))
    if ease_factor < 1.3:
        ease_factor = 1.3

    # Вычисляем следующую дату повторения
    # Убеждаемся, что интервал - это целое число дней
    days_to_add = int(round(interval))
    due_date = datetime.now(timezone.utc) + timedelta(days=days_to_add)
    
    return {
        'repetitions': repetitions,
        'interval': interval,
        'ease_factor': ease_factor,
        'due_date': due_date.strftime('%Y-%m-%dT%H:%M:%SZ') # Формат для БД
    }