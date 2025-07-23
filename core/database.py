import sqlite3
import json
import logging

# Настраиваем логирование, чтобы видеть, что происходит внутри модуля
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = 'phraseweaver.db'

class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        """
        Инициализатор класса. Сохраняет имя файла БД и вызывает метод
        для создания таблиц.
        """
        self.db_name = db_name
        self.conn = None
        self._init_db()

    def _get_connection(self):
        """
        Устанавливает соединение с базой данных.
        Использование `isolation_level=None` (autocommit) упрощает транзакции
        для простых операций. Для сложных будем использовать `with self.conn:`.
        """
        try:
            # `check_same_thread=False` - важное требование для Kivy/многопоточных
            # приложений, так как к БД могут обращаться из разных потоков (например, UI и фоновый).
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            return self.conn
        except sqlite3.Error as e:
            logging.error(f"Database connection error: {e}")
            return None

    def _init_db(self):
        """
        Создает таблицы в БД, если они еще не существуют.
        Выполняется один раз при создании объекта DatabaseManager.
        """
        create_decks_table_sql = """
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        """
        
        create_concepts_table_sql = """
        CREATE TABLE IF NOT EXISTS concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            full_sentence TEXT NOT NULL,
            keyword_phrase TEXT NOT NULL,
            translations TEXT, -- Храним как JSON-строку
            examples TEXT, -- Храним как JSON-строку
            audio_paths TEXT, -- Храним как JSON-строку
            FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
        );
        """
        
        create_cards_table_sql = """
        CREATE TABLE IF NOT EXISTS training_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_id INTEGER NOT NULL,
            card_type TEXT NOT NULL, -- 'forward', 'reverse', 'cloze'
            front TEXT NOT NULL,
            back TEXT NOT NULL,
            srs_level INTEGER DEFAULT 0,
            due_date TEXT NOT NULL, -- ISO 8601 format: YYYY-MM-DDTHH:MM:SS
            FOREIGN KEY (concept_id) REFERENCES concepts (id) ON DELETE CASCADE
        );
        """
        # ON DELETE CASCADE означает, что при удалении колоды/концепта,
        # все связанные с ним карточки/концепты тоже удалятся. Это очень удобно.

        conn = self._get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                logging.info("Initializing database schema...")
                cursor.execute(create_decks_table_sql)
                cursor.execute(create_concepts_table_sql)
                cursor.execute(create_cards_table_sql)
                conn.commit()
                logging.info("Database schema initialized successfully.")
            except sqlite3.Error as e:
                logging.error(f"Error creating tables: {e}")
            finally:
                conn.close()

    # --- Методы для работы с Колодами (Decks) ---

    def create_deck(self, name):
        """
        Создает новую колоду с заданным именем.
        Возвращает ID новой колоды или None в случае ошибки.
        """
        sql = "INSERT INTO decks (name) VALUES (?)"
        conn = self._get_connection()
        if conn:
            try:
                with conn: # `with conn:` автоматически управляет транзакцией
                    cursor = conn.cursor()
                    cursor.execute(sql, (name,))
                    logging.info(f"Deck '{name}' created with id {cursor.lastrowid}.")
                    return cursor.lastrowid
            except sqlite3.IntegrityError:
                logging.warning(f"Deck '{name}' already exists.")
                return None
            except sqlite3.Error as e:
                logging.error(f"Error creating deck: {e}")
                return None

    def get_all_decks(self):
        """
        Возвращает список всех колод.
        Каждая колода - это словарь {'id': ..., 'name': ...}.
        """
        sql = "SELECT id, name FROM decks ORDER BY name"
        conn = self._get_connection()
        if conn:
            try:
                # Устанавливаем `row_factory`, чтобы получать результаты в виде словарей,
                # а не кортежей. Это гораздо удобнее.
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(sql)
                decks = [dict(row) for row in cursor.fetchall()]
                logging.info(f"Retrieved {len(decks)} decks from DB.")
                return decks
            except sqlite3.Error as e:
                logging.error(f"Error fetching decks: {e}")
                return [] # Возвращаем пустой список в случае ошибки
        return []

    def close(self):
        """Закрывает соединение с БД, если оно открыто."""
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed.")