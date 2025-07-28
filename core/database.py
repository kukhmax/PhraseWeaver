# Файл: core/database.py (ФИНАЛЬНАЯ ВЕРСИЯ v4)
import sqlite3, logging, json, re
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - DB - %(levelname)s - %(message)s')
DB_NAME = 'phraseweaver.db'

class DatabaseManager:
    # ... (все методы до update_card_srs без изменений, но я привожу их для полноты)
    
    def __init__(self, db_name=DB_NAME): self._db_name=db_name; self._init_db()
    
    def _get_connection(self):
        try: conn = sqlite3.connect(self._db_name, check_same_thread=False); conn.row_factory=sqlite3.Row; return conn
        except: return None
    
    def _init_db(self):
        """
        Инициализирует/обновляет схему базы данных.
        Создает таблицы, если они не существуют, и выполняет миграции.
        """
        conn = self._get_connection()
        if not conn: 
            return
        try:
            with conn:
                cursor = conn.cursor()
                # --- Существующие таблицы (без изменений) ---
                cursor.execute("CREATE TABLE IF NOT EXISTS decks (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, lang_code TEXT NOT NULL DEFAULT 'en')")
                cursor.execute("CREATE TABLE IF NOT EXISTS concepts (id INTEGER PRIMARY KEY, deck_id INTEGER, keyword TEXT NOT NULL, translation TEXT, full_sentence TEXT, image_path TEXT, FOREIGN KEY (deck_id) REFERENCES decks (id))")
                cursor.execute("CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY, concept_id INTEGER, deck_id INTEGER, front TEXT NOT NULL, back TEXT NOT NULL, card_type TEXT NOT NULL, due_date DATE DEFAULT (date('now')), interval REAL DEFAULT 1, ease_factor REAL DEFAULT 2.5, repetitions INTEGER DEFAULT 0, FOREIGN KEY (concept_id) REFERENCES concepts (id), FOREIGN KEY (deck_id) REFERENCES decks (id))")
                cursor.execute("CREATE TABLE IF NOT EXISTS review_history (id INTEGER PRIMARY KEY, card_id INTEGER, review_date TEXT, FOREIGN KEY (card_id) REFERENCES cards (id))")
                
                # --- ИЗМЕНЕНИЕ 1: Создаем новую таблицу для настроек ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)

                # --- ИЗМЕНЕНИЕ 2: Устанавливаем настройку по умолчанию ---
                # ON CONFLICT(key) DO NOTHING значит, что если настройка 'target_language'
                # уже существует, эта команда ничего не сделает.
                cursor.execute("""
                    INSERT INTO settings (key, value) VALUES ('target_language', 'ru')
                    ON CONFLICT(key) DO NOTHING
                """)
                cursor.execute("""
                    INSERT INTO settings (key, value) VALUES ('ui_language', 'ru')
                    ON CONFLICT(key) DO NOTHING
                """)

                cursor.execute("PRAGMA table_info(concepts)")
                if 'image_path' not in [col[1] for col in cursor.fetchall()]:
                    cursor.execute("ALTER TABLE concepts ADD COLUMN image_path TEXT")

                logging.info("Схема БД успешно инициализирована/обновлена.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при инициализации таблиц: {e}")
        finally:
            if conn: conn.close()
    
    def create_deck(self, name: str, lang_code: str):
        conn=self._get_connection();
        if not conn: return None
        try:
            with conn: c=conn.cursor(); c.execute("INSERT INTO decks (name, lang_code) VALUES (?, ?)", (name, lang_code)); return c.lastrowid
        except: return None
        finally: conn.close()
    
    def get_all_decks(self):
        conn=self._get_connection();
        if not conn: return []
        try: c=conn.cursor(); c.execute("SELECT id, name, lang_code FROM decks ORDER BY name"); return [dict(row) for row in c.fetchall()]
        except: return []
        finally: conn.close()
    
    def create_concept_and_cards(self, deck_id: int, keyword: str, original_keyword: str, enriched_data: dict) -> int | str | None:
        translation, image_path, audio_path = enriched_data.get('translation'), enriched_data.get('image_path'), enriched_data.get('audio_path')
        if not keyword: return None
        conn = self._get_connection();
        if not conn: return None
        try:
            with conn:
                c=conn.cursor(); c.execute("SELECT id FROM concepts WHERE keyword = ? AND deck_id = ?", (keyword, deck_id))
                if c.fetchone(): return "duplicate"
                c.execute("INSERT INTO concepts (deck_id, keyword, translation, full_sentence, image_path) VALUES (?, ?, ?, ?, ?)",(deck_id, keyword, translation, keyword, image_path))
                concept_id = c.lastrowid
                logging.info(f"Концепт '{keyword[:30]}' создан с ID {concept_id}")
                cards = self._generate_cards_for_concept(concept_id, deck_id, keyword, translation, image_path, audio_path, original_keyword)
                if cards:
                    c.executemany("INSERT INTO cards (concept_id, deck_id, front, back, card_type) VALUES (?, ?, ?, ?, ?)", cards)
                    logging.info(f"Создано {len(cards)} карточек для концепта ID {concept_id}")
            return concept_id
        finally: conn.close()
    
    def _generate_cards_for_concept(self, c_id, d_id, p, t, i_p, a_p, ok):
        cards=[]
        cards.append((c_id, d_id, json.dumps({'text': p, 'image': i_p, 'audio': a_p}), t, "direct_recognition"))
        cards.append((c_id, d_id, json.dumps({'text': t, 'image': i_p}), p, "reverse_recall"))
        if ok and re.search(re.escape(ok), p, re.IGNORECASE):
            ctx=re.sub(re.escape(ok), "______", p, flags=re.IGNORECASE)
            cards.append((c_id, d_id, json.dumps({'text': ctx, 'image': i_p, 'audio': a_p}), ok, "context_cloze"))
        return cards
    
    def count_all_cards_in_deck(self, d_id):
        conn=self._get_connection();
        if not conn: return 0
        try: c=conn.cursor(); c.execute("SELECT COUNT(id) FROM cards WHERE deck_id = ?", (d_id,)); return c.fetchone()[0]
        except: return 0
        finally: conn.close()
    
    def count_cards_for_review(self, d_id):
        conn=self._get_connection();
        if not conn: return 0
        try:
            now_utc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            c=conn.cursor(); c.execute("SELECT COUNT(id) FROM cards WHERE deck_id = ? AND due_date <= ?", (d_id, now_utc)); return c.fetchone()[0]
        except: return 0
        finally: conn.close()
    
    def get_cards_for_review(self, d_id, limit=20):
        now_utc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        sql="SELECT id, front, back, card_type, repetitions, interval, ease_factor FROM cards WHERE deck_id = ? AND due_date <= ? ORDER BY due_date LIMIT ?"
        conn=self._get_connection();
        if not conn: return []
        try: c=conn.cursor(); c.execute(sql, (d_id, now_utc, limit)); return [dict(row) for row in c.fetchall()]
        finally: conn.close()

    def update_card_srs(self, card_id: int, due_date: str, interval: float, ease_factor: float, repetitions: int):
        """Обновляет SRS-данные, принимая правильные именованные аргументы."""
        sql = "UPDATE cards SET due_date = ?, interval = ?, ease_factor = ?, repetitions = ? WHERE id = ?"
        conn = self._get_connection()
        if not conn:
            return False
        try:
            with conn:
                cursor = conn.cursor()
                # Передаем значения в правильном порядке
                cursor.execute(sql, (due_date, interval, ease_factor, repetitions, card_id))
            return True
        finally:
            if conn:
                conn.close()

    def get_reviews_per_day(self, days: int = 7) -> dict:
        """
        Возвращает количество повторений за каждый из последних N дней.
        Результат: {'2025-07-27': 50, '2025-07-26': 32, ...}
        """
        today = datetime.now(timezone.utc).date()
        date_list = [today - timedelta(days=i) for i in range(days)]
        
        # Запрос группирует все записи по дате и считает их
        sql = """
            SELECT 
                substr(review_date, 1, 10) as review_day, 
                COUNT(id) as count 
            FROM review_history 
            WHERE review_day >= ?
            GROUP BY review_day
        """
        
        start_date = (today - timedelta(days=days-1)).strftime('%Y-%m-%d')
        
        conn = self._get_connection()
        if not conn: return {}
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (start_date,))
            
            # Создаем словарь {дата: количество} из ответа БД
            db_results = {row['review_day']: row['count'] for row in cursor.fetchall()}
            
            # Заполняем пропущенные дни нулями для красивого графика
            final_stats = {dt.strftime('%Y-%m-%d'): db_results.get(dt.strftime('%Y-%m-%d'), 0) for dt in date_list}
            return final_stats
            
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении статистики по дням: {e}")
            return {}
        finally:
            if conn: conn.close()
    
    def get_study_streak(self) -> int:
        """Вычисляет 'ударную серию' - количество дней занятий без перерыва."""
        sql = "SELECT DISTINCT substr(review_date, 1, 10) as review_day FROM review_history ORDER BY review_day DESC"
        conn = self._get_connection()
        if not conn: return 0
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            
            dates = [datetime.strptime(row['review_day'], '%Y-%m-%d').date() for row in cursor.fetchall()]
            if not dates: return 0

            streak = 0
            today = datetime.now(timezone.utc).date()
            
            # Если сегодня занимался, начинаем с 1
            if dates[0] == today:
                streak = 1
                yesterday = today - timedelta(days=1)
                # Идем по остальным дням
                for i in range(1, len(dates)):
                    if dates[i] == yesterday:
                        streak += 1
                        yesterday -= timedelta(days=1)
                    else:
                        break # Нашли разрыв, останавливаемся
            # Если сегодня не занимался, но вчера - да
            elif dates[0] == (today - timedelta(days=1)):
                 streak = 1 # начинаем со вчера
                 yesterday = today - timedelta(days=2)
                 for i in range(1, len(dates)):
                    if dates[i] == yesterday:
                        streak += 1
                        yesterday -= timedelta(days=1)
                    else:
                        break
            
            return streak

        except sqlite3.Error as e:
            logging.error(f"Ошибка при подсчете ударной серии: {e}")
            return 0
        finally:
            if conn: conn.close()

    def count_learned_cards(self) -> int:
        """Считает количество 'выученных' карточек (интервал > 21 дня)."""
        sql = "SELECT COUNT(id) FROM cards WHERE interval >= 21"
        conn = self._get_connection()
        if not conn: return 0
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logging.error(f"Ошибка при подсчете выученных карточек: {e}")
            return 0
        finally:
            if conn: conn.close()

    def get_setting(self, key: str, default: str = None) -> str:
        """Получает значение настройки по ключу."""
        conn = self._get_connection()
        if not conn: return default
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default
        finally:
            if conn: conn.close()

    def set_setting(self, key: str, value: str):
        """Сохраняет или обновляет значение настройки."""
        sql = "REPLACE INTO settings (key, value) VALUES (?, ?)"
        conn = self._get_connection()
        if not conn: return
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (key, value))
            logging.info(f"Настройка '{key}' установлена в '{value}'.")
        finally:
            if conn: conn.close()