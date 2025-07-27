# Файл: core/database.py (ОКОНЧАТЕЛЬНАЯ ВЕРСИЯ v2)

import sqlite3
import logging
from datetime import datetime, timezone
import json
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - DB - %(levelname)s - %(message)s')
DB_NAME = 'phraseweaver.db'

class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self._db_name = db_name
        self._init_db()

    def _get_connection(self):
        try:
            conn = sqlite3.connect(self._db_name, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logging.error(f"Ошибка соединения с БД: {e}")
            return None

    def _init_db(self):
        conn = self._get_connection()
        if not conn: return
        try:
            with conn:
                # Везде исправлено на conn.cursor()
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS decks (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, lang_code TEXT NOT NULL DEFAULT 'en')")
                cursor.execute("CREATE TABLE IF NOT EXISTS concepts (id INTEGER PRIMARY KEY, deck_id INTEGER, keyword TEXT NOT NULL, translation TEXT, full_sentence TEXT, image_path TEXT, FOREIGN KEY (deck_id) REFERENCES decks (id))")
                cursor.execute("CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY, concept_id INTEGER, deck_id INTEGER, front TEXT NOT NULL, back TEXT NOT NULL, card_type TEXT NOT NULL, due_date DATE DEFAULT (date('now')), interval INTEGER DEFAULT 1, ease_factor REAL DEFAULT 2.5, repetitions INTEGER DEFAULT 0, FOREIGN KEY (concept_id) REFERENCES concepts (id), FOREIGN KEY (deck_id) REFERENCES decks (id))")
                cursor.execute("PRAGMA table_info(concepts)")
                if 'image_path' not in [col[1] for col in cursor.fetchall()]:
                    cursor.execute("ALTER TABLE concepts ADD COLUMN image_path TEXT")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при инициализации/миграции таблиц: {e}")
        finally:
            if conn: conn.close()

    def create_deck(self, name: str, lang_code: str):
        conn = self._get_connection()
        if not conn: return None
        try:
            with conn:
                cursor = conn.cursor() # ИСПРАВЛЕНО
                cursor.execute("INSERT INTO decks (name, lang_code) VALUES (?, ?)", (name, lang_code))
                return cursor.lastrowid
        except sqlite3.IntegrityError: return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании колоды: {e}"); return None
        finally:
            if conn: conn.close()
    
    def get_all_decks(self):
        conn = self._get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor() # ИСПРАВЛЕНО
            cursor.execute("SELECT id, name, lang_code FROM decks ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Ошибка получения колод: {e}"); return []
        finally:
            if conn: conn.close()
    
    def create_concept_and_cards(self, deck_id: int, keyword: str, original_keyword: str, enriched_data: dict) -> int | str | None:
        translation = enriched_data.get('translation')
        image_path = enriched_data.get('image_path')
        audio_path = enriched_data.get('audio_path')
        if not keyword: return None
        conn = self._get_connection()
        if not conn: return None
        try:
            with conn:
                cursor = conn.cursor() # ИСПРАВЛЕНО
                cursor.execute("SELECT id FROM concepts WHERE keyword = ? AND deck_id = ?", (keyword, deck_id))
                if cursor.fetchone(): return "duplicate"
                cursor.execute("INSERT INTO concepts (deck_id, keyword, translation, full_sentence, image_path) VALUES (?, ?, ?, ?, ?)", (deck_id, keyword, translation, keyword, image_path))
                concept_id = cursor.lastrowid
                logging.info(f"Концепт '{keyword[:30]}' создан с ID {concept_id}")
                cards = self._generate_cards_for_concept(concept_id, deck_id, keyword, translation, image_path, audio_path, original_keyword)
                if cards:
                    cursor.executemany("INSERT INTO cards (concept_id, deck_id, front, back, card_type) VALUES (?, ?, ?, ?, ?)", cards)
                    logging.info(f"Создано {len(cards)} карточек для концепта ID {concept_id}")
            return concept_id
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании концепта: {e}"); return None
        finally:
            if conn: conn.close()

    def _generate_cards_for_concept(self, concept_id: int, deck_id: int, phrase: str, translation: str, image_path: str, audio_path: str, original_keyword: str) -> list[tuple]:
        cards = []
        front_direct = json.dumps({'text': phrase, 'image': image_path, 'audio': audio_path})
        cards.append((concept_id, deck_id, front_direct, translation, "direct_recognition"))
        front_recall = json.dumps({'text': translation, 'image': image_path})
        cards.append((concept_id, deck_id, front_recall, phrase, "reverse_recall"))
        if original_keyword and re.search(re.escape(original_keyword), phrase, re.IGNORECASE):
            context_sentence = re.sub(re.escape(original_keyword), "______", phrase, flags=re.IGNORECASE)
            front_context = json.dumps({'text': context_sentence, 'image': image_path, 'audio': audio_path})
            back_context = original_keyword
            cards.append((concept_id, deck_id, front_context, back_context, "context_cloze"))
        return cards

    def count_all_cards_in_deck(self, deck_id: int) -> int:
        conn = self._get_connection();
        if not conn: return 0
        try:
            cursor = conn.cursor() # ИСПРАВЛЕНО
            cursor.execute("SELECT COUNT(id) FROM cards WHERE deck_id = ?", (deck_id,))
            return cursor.fetchone()[0]
        except: return 0
        finally: conn.close()

    def count_cards_for_review(self, deck_id: int) -> int:
        conn = self._get_connection();
        if not conn: return 0
        try:
            now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            cursor = conn.cursor() # ИСПРАВЛЕНО
            cursor.execute("SELECT COUNT(id) FROM cards WHERE deck_id = ? AND due_date <= ?", (deck_id, now_utc))
            return cursor.fetchone()[0]
        except: return 0
        finally: conn.close()

    def get_cards_for_review(self, deck_id: int, limit: int = 20) -> list:
        now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        sql = "SELECT id, front, back, card_type, repetitions, interval, ease_factor FROM cards WHERE deck_id = ? AND due_date <= ? ORDER BY due_date LIMIT ?"
        conn = self._get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor() # ИСПРАВЛЕНО
            cursor.execute(sql, (deck_id, now_utc, limit))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении карточек для повторения: {e}")
            return []
        finally:
            if conn: conn.close()

    def update_card_srs(self, card_id: int, new_due_date: str, new_interval: float, new_ease: float, new_reps: int):
        sql = "UPDATE cards SET due_date = ?, interval = ?, ease_factor = ?, repetitions = ? WHERE id = ?"
        conn = self._get_connection()
        if not conn: return False
        try:
            with conn:
                cursor = conn.cursor() # ИСПРАВЛЕНО
                cursor.execute(sql, (new_due_date, new_interval, new_ease, new_reps, card_id))
            return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при обновлении SRS карточки {card_id}: {e}")
            return False
        finally:
            if conn: conn.close()