from datetime import datetime, timedelta, timezone

# Константа для начальной даты. Новые карточки должны быть показаны сегодня.
INITIAL_DUE_DATE = datetime.now(timezone.utc).isoformat()

# Простейшие интервалы для SRS. В реальном приложении они были бы сложнее.
# Ключ - текущий уровень SRS, значение - на сколько дней сдвинуть дату.
SRS_INTERVALS = {
    0: timedelta(days=0),     # Снова - показать сегодня
    1: timedelta(days=1),     # Хорошо - завтра
    2: timedelta(days=3),     # Хорошо - через 3 дня
    3: timedelta(days=7),     # Хорошо - через неделю
    4: timedelta(days=14),
    5: timedelta(days=30),
    6: timedelta(days=90),
    # и т.д.
}
MAX_SRS_LEVEL = max(SRS_INTERVALS.keys())

def calculate_next_due_date(current_srs_level: int, quality: str) -> tuple[int, str]:
    """
    Вычисляет новый уровень SRS и дату следующего повторения.
    
    :param current_srs_level: Текущий уровень карточки (0, 1, 2...).
    :param quality: Оценка ответа ("again", "good", "easy").
    :return: Кортеж (new_srs_level, new_due_date_iso).
    """
    new_srs_level = current_srs_level

    if quality == "again":
        new_srs_level = 0 # Сбрасываем прогресс
    elif quality == "good":
        new_srs_level = min(current_srs_level + 1, MAX_SRS_LEVEL)
    elif quality == "easy":
        # При "легко" перескакиваем через один уровень для ускорения
        new_srs_level = min(current_srs_level + 2, MAX_SRS_LEVEL)

    # Вычисляем интервал и новую дату
    interval = SRS_INTERVALS.get(new_srs_level, timedelta(days=90))
    # Для "again" показываем через 10 минут, а не сразу, чтобы избежать зацикливания
    if quality == "again":
        interval = timedelta(minutes=10)

    new_due_date = datetime.now(timezone.utc) + interval
    
    return new_srs_level, new_due_date.isoformat()