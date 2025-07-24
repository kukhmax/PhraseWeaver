import sqlite3
import json
import logging
from datetime import datetime, timezone

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

    def get_cards_for_review(self, deck_id: int, limit: int = 20) -> list:
        """
        Возвращает список карточек из указанной колоды, которые пора повторить.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        sql = """
        SELECT tc.id, tc.front, tc.back, tc.srs_level, tc.card_type, c.examples
        FROM training_cards tc
        JOIN concepts c ON tc.concept_id = c.id
        WHERE c.deck_id = ? AND tc.due_date <= ?
        ORDER BY tc.due_date
        LIMIT ?
        """
        conn = self._get_connection()
        if conn:
            try:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(sql, (deck_id, now_iso, limit))
                cards = [dict(row) for row in cursor.fetchall()]
                logging.info(f"Найдено {len(cards)} карточек для повторения в колоде {deck_id}.")
                return cards
            except sqlite3.Error as e:
                logging.error(f"Ошибка при получении карточек для повторения: {e}")
        return []

    def count_cards_for_review(self, deck_id: int) -> int:
        """Считает количество карточек для повторения в колоде."""
        now_iso = datetime.now(timezone.utc).isoformat()
        sql = """
        SELECT COUNT(tc.id)
        FROM training_cards tc
        JOIN concepts c ON tc.concept_id = c.id
        WHERE c.deck_id = ? AND tc.due_date <= ?
        """
        conn = self._get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(sql, (deck_id, now_iso))
                return cursor.fetchone()[0]
            except sqlite3.Error as e:
                logging.error(f"Ошибка при подсчете карточек: {e}")
        return 0

    def update_card_srs(self, card_id: int, new_srs_level: int, new_due_date: str):
        """Обновляет SRS-данные карточки."""
        sql = "UPDATE training_cards SET srs_level = ?, due_date = ? WHERE id = ?"
        conn = self._get_connection()
        if conn:
            try:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute(sql, (new_srs_level, new_due_date, card_id))
                    logging.info(f"Карточка ID {card_id} обновлена: уровень {new_srs_level}, дата {new_due_date}")
                    return True
            except sqlite3.Error as e:
                logging.error(f"Ошибка при обновлении карточки: {e}")
        return False

    # --- Методы для работы с Концептами и Карточками ---

    def create_concept_and_cards(self, deck_id, full_sentence, enriched_data):
        """
        Создает новый "Концепт" и автоматически генерирует для него
        тренировочные карточки. Это транзакционная операция.
        """
        # 1. Готовим данные для сохранения
        keyword_phrase = enriched_data['keyword_phrase']
        translations = json.dumps(enriched_data['translation']) # Сохраняем как JSON
        examples = json.dumps(enriched_data['examples'])
        audio_paths = json.dumps(enriched_data['audio_paths'])
        
        # Проверка на дубликат по ключевой фразе
        check_sql = "SELECT id FROM concepts WHERE keyword_phrase = ?"
        # Код создания концепта
        concept_sql = """
        INSERT INTO concepts (deck_id, full_sentence, keyword_phrase, translations, examples, audio_paths)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        conn = self._get_connection()
        if not conn:
            return None
            
        try:
            with conn: # `with conn` обеспечивает, что вся операция будет одной транзакцией
                cursor = conn.cursor()
                
                # Проверяем, не существует ли уже такая ключевая фраза
                cursor.execute(check_sql, (keyword_phrase,))
                if cursor.fetchone():
                    logging.warning(f"Концепт с фразой '{keyword_phrase}' уже существует. Сохранение отменено.")
                    return "duplicate" # Возвращаем специальный маркер

                # 2. Создаем Концепт
                cursor.execute(concept_sql, (deck_id, full_sentence, keyword_phrase, translations, examples, audio_paths))
                concept_id = cursor.lastrowid
                logging.info(f"Концепт '{keyword_phrase}' создан с ID {concept_id}")

                # 3. Генерируем и создаем Карточки
                self._generate_cards_for_concept(cursor, concept_id, enriched_data)
                
                return concept_id

        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании концепта и карточек: {e}")
            return None

    def _generate_cards_for_concept(self, cursor, concept_id, enriched_data):
        """Вспомогательный метод для генерации карточек. Вызывается внутри транзакции."""
        from datetime import datetime, timezone
        from core.srs import INITIAL_DUE_DATE # Импортируем, чтобы избежать циклической зависимости

        keyword = enriched_data['keyword_phrase']
        translation = enriched_data.get('translation')
        full_sentence = enriched_data.get('full_sentence', '') # Возьмем из enriched_data, если передадим

        # Дата "сегодня" для новых карточек
        due_date = INITIAL_DUE_DATE

        cards_to_create = []

        # Карточка 1: Прямая (Ключевая фраза -> Перевод)
        if translation:
            cards_to_create.append({
                'concept_id': concept_id, 'card_type': 'forward',
                'front': keyword, 'back': translation,
                'due_date': due_date
            })

        # Карточка 2: Обратная (Перевод -> Ключевая фраза)
        if translation:
            cards_to_create.append({
                'concept_id': concept_id, 'card_type': 'reverse',
                'front': translation, 'back': keyword,
                'due_date': due_date
            })
            
        # Карточка 3: Заполнить пропуск
        if full_sentence and keyword in full_sentence:
            cloze_sentence = full_sentence.replace(keyword, "______")
            cards_to_create.append({
                'concept_id': concept_id, 'card_type': 'cloze',
                'front': cloze_sentence, 'back': full_sentence,
                'due_date': due_date
            })

        card_sql = """
        INSERT INTO training_cards (concept_id, card_type, front, back, due_date, srs_level)
        VALUES (:concept_id, :card_type, :front, :back, :due_date, 0)
        """
        cursor.executemany(card_sql, cards_to_create)
        logging.info(f"Создано {len(cards_to_create)} карточек для концепта ID {concept_id}")

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