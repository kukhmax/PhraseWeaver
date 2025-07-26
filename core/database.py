# Файл: core/database.py

import sqlite3
import logging
from datetime import datetime, timezone

# Настраиваем логирование, чтобы видеть, что происходит внутри модуля
logging.basicConfig(level=logging.INFO, format='%(asctime)s - DB - %(levelname)s - %(message)s')

DB_NAME = 'phraseweaver.db'

class DatabaseManager:
    """
    Класс для управления всеми операциями с базой данных SQLite.
    """
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self._init_db()

    def _get_connection(self):
        """Возвращает новое соединение с БД."""
        try:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            # Устанавливаем `row_factory`, чтобы получать результаты в виде словарей
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logging.error(f"Ошибка соединения с БД: {e}")
            return None

    def _init_db(self):
        """
        Инициализирует/обновляет схему базы данных.
        Создает таблицы, если они не существуют, и выполняет миграции.
        """
        logging.info("Инициализация схемы БД...")
        conn = self._get_connection()
        if not conn: return

        try:
            with conn:
                cursor = conn.cursor()
                # --- Создание таблиц (если их нет) ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS decks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        lang_code TEXT NOT NULL DEFAULT 'en'
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS concepts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        deck_id INTEGER NOT NULL,
                        keyword TEXT NOT NULL,
                        translation TEXT,
                        full_sentence TEXT,
                        image_path TEXT,
                        FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        concept_id INTEGER NOT NULL,
                        deck_id INTEGER NOT NULL,
                        front TEXT NOT NULL,
                        back TEXT NOT NULL,
                        card_type TEXT NOT NULL,
                        due_date TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                        interval REAL DEFAULT 1.0,
                        ease_factor REAL DEFAULT 2.5,
                        repetitions INTEGER DEFAULT 0,
                        FOREIGN KEY (concept_id) REFERENCES concepts (id) ON DELETE CASCADE,
                        FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
                    )
                """)
                
                # --- Процесс миграции для старых БД ---
                logging.info("Проверка необходимости миграции...")
                cursor.execute("PRAGMA table_info(concepts)")
                columns = [col['name'] for col in cursor.fetchall()]
                if 'image_path' not in columns:
                    logging.info("Миграция: добавляю 'image_path' в 'concepts'.")
                    cursor.execute("ALTER TABLE concepts ADD COLUMN image_path TEXT")
                
                logging.info("Схема БД успешно инициализирована/обновлена.")

        except sqlite3.Error as e:
            logging.error(f"Ошибка при инициализации/миграции таблиц: {e}")
        finally:
            conn.close()

    # --- Методы для Колоды (Decks) ---
    def create_deck(self, name: str, lang_code: str):
        sql = "INSERT INTO decks (name, lang_code) VALUES (?, ?)"
        conn = self._get_connection()
        if not conn: return None
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (name, lang_code))
                deck_id = cursor.lastrowid
                logging.info(f"Колода '{name}' (язык: {lang_code}) создана с ID {deck_id}.")
                return deck_id
        except sqlite3.IntegrityError:
            logging.warning(f"Колода '{name}' уже существует.")
            return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании колоды: {e}")
            return None
        finally:
            if conn: conn.close()
    
    def get_all_decks(self):
        sql = "SELECT id, name, lang_code FROM decks ORDER BY name"
        conn = self._get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Ошибка получения колод: {e}")
            return []
        finally:
            if conn: conn.close()

    # --- Методы для Концептов и Карточек ---
    def create_concept_and_cards(self, deck_id: int, full_sentence: str, enriched_data: dict) -> int | str | None:
        """
        Создает новый 'концепт' и связанные с ним карточки.
        """
        keyword = enriched_data.get('keyword')
        translation = enriched_data.get('translation')
        image_path = enriched_data.get('image_path')
        audio_path = enriched_data.get('audio_path')

        if not keyword:
            logging.error("Попытка сохранить концепт без ключевой фразы.")
            return None

        conn = self._get_connection()
        if not conn: return None
        try:
            with conn:
                cursor = conn.cursor()
                # Проверка на дубликаты
                cursor.execute("SELECT id FROM concepts WHERE keyword = ? AND deck_id = ?", (keyword, deck_id))
                if cursor.fetchone():
                    return "duplicate"

                # Создание концепта
                cursor.execute(
                    "INSERT INTO concepts (deck_id, keyword, translation, full_sentence, image_path) VALUES (?, ?, ?, ?, ?)",
                    (deck_id, keyword, translation, full_sentence, image_path)
                )
                concept_id = cursor.lastrowid
                logging.info(f"Концепт '{keyword}' создан с ID {concept_id}")

                # Генерация и вставка карточек
                cards = self._generate_cards_for_concept(concept_id, deck_id, keyword, translation, audio_path)
                if cards:
                    cursor.executemany(
                        "INSERT INTO cards (concept_id, deck_id, front, back, card_type) VALUES (?, ?, ?, ?, ?)",
                        cards
                    )
                    logging.info(f"Создано {len(cards)} карточек для концепта ID {concept_id}")
            return concept_id
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании концепта: {e}")
            return None
        finally:
            if conn: conn.close()

    def _generate_cards_for_concept(self, concept_id: int, deck_id: int, keyword: str, translation: str, audio_path: str) -> list[tuple]:
        """
        Приватный метод для генерации стандартного набора карточек.
        """
        cards = []
        if keyword and translation:
            # Прямая карточка
            back_with_audio = f"{translation}\n[sound:{audio_path}]" if audio_path else translation
            cards.append((concept_id, deck_id, keyword, back_with_audio, "direct"))
            # Обратная карточка
            cards.append((concept_id, deck_id, translation, keyword, "reverse"))
        return cards
    
    # --- Методы для Тренировки ---
    def count_cards_for_review(self, deck_id: int) -> int:
        """Считает количество карточек для повторения в колоде."""
        now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        sql = "SELECT COUNT(id) FROM cards WHERE deck_id = ? AND due_date <= ?"
        conn = self._get_connection()
        if not conn: return 0
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (deck_id, now_utc))
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logging.error(f"Ошибка при подсчете карточек: {e}")
            return 0
        finally:
            if conn: conn.close()

    def get_cards_for_review(self, deck_id: int, limit: int = 20) -> list:
        """Возвращает список карточек из указанной колоды, которые пора повторить."""
        now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        sql = "SELECT id, front, back FROM cards WHERE deck_id = ? AND due_date <= ? ORDER BY due_date LIMIT ?"
        conn = self._get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (deck_id, now_utc, limit))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении карточек для повторения: {e}")
            return []
        finally:
            if conn: conn.close()

    def update_card_srs(self, card_id: int, new_due_date: str, new_interval: float, new_ease: float, new_reps: int):
        """Обновляет SRS-данные карточки после ответа."""
        sql = """
        UPDATE cards 
        SET due_date = ?, interval = ?, ease_factor = ?, repetitions = ? 
        WHERE id = ?
        """
        conn = self._get_connection()
        if not conn: return False
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (new_due_date, new_interval, new_ease, new_reps, card_id))
                return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при обновлении SRS карточки {card_id}: {e}")
            return False
        finally:
            if conn: conn.close()