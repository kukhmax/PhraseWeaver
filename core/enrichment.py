# Файл: core/enrichment.py

import asyncio
import logging
import os
import hashlib
from pathlib import Path
import aiohttp
# --- ИЗМЕНЕНИЕ: Импортируем наш новый AI-генератор ---
from core.ai_generator import generate_examples_with_ai
from duckduckgo_search import AsyncDDGS
from gtts import gTTS
from googletrans import Translator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - ENRICH - %(levelname)s - %(message)s')
AUDIO_DIR = Path("assets/audio")
IMAGE_DIR = Path("assets/images")

def ensure_dir_exists(*dirs):
    for dir_path in dirs:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)

ensure_dir_exists(AUDIO_DIR, IMAGE_DIR)

# ... (функции get_translation, find_image_for_keyword, generate_audio остаются БЕЗ ИЗМЕНЕНИЙ) ...
# (здесь должен быть твой код для этих трех функций, я его опускаю для краткости)
# Я скопирую их из предыдущего ответа для полноты картины

async def get_translation(text: str, from_lang: str, to_lang: str = 'ru') -> str | None:
    logging.info(f"Перевод: '{text}' с {from_lang} на {to_lang}")
    try:
        loop = asyncio.get_running_loop()
        def translate_sync():
            translator = Translator()
            translation_result = translator.translate(text, src=from_lang, dest=to_lang)
            return translation_result.text
        translated_text = await loop.run_in_executor(None, translate_sync)
        logging.info(f"Перевод получен: '{translated_text}'")
        return translated_text
    except Exception as e:
        logging.error(f"Ошибка перевода: {e}")
        return None

async def find_image_for_keyword(keyword: str) -> str | None:
    logging.info(f"Поиск картинки для '{keyword}'...")
    try:
        async with AsyncDDGS() as ddgs:
            results = await ddgs.images(keyword, max_results=1)
            if not results:
                logging.warning("Картинки не найдены.")
                return None
            
            image_url = results[0].get('image')
            if not image_url: return None

            logging.info(f"Найдена картинка: {image_url}")
            file_hash = hashlib.md5(keyword.encode()).hexdigest()
            extension = os.path.splitext(image_url.split('?')[0])[-1] or '.jpg'
            image_path = IMAGE_DIR / f"{file_hash}{extension}"

            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        with open(image_path, 'wb') as f:
                            f.write(await response.read())
                        logging.info(f"Картинка сохранена: {image_path}")
                        return str(image_path)
    except Exception as e:
        logging.error(f"Ошибка поиска/скачивания картинки: {e}")
    return None

async def generate_audio(text: str, lang: str, filename_prefix: str) -> str | None:
    logging.info(f"Генерация аудио для: '{text}' ({lang})")
    try:
        file_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        output_path = AUDIO_DIR / f"{filename_prefix}_{file_hash}.mp3"

        if output_path.exists():
            logging.info(f"Аудиофайл уже существует: {output_path}")
            return str(output_path)
        
        loop = asyncio.get_running_loop()
        tts = await loop.run_in_executor(None, lambda: gTTS(text=text, lang=lang, slow=False))
        await loop.run_in_executor(None, tts.save, str(output_path))
        
        logging.info(f"Аудио сохранено: {output_path}")
        return str(output_path)
    except Exception as e:
        logging.error(f"Ошибка генерации аудио: {e}")
        return None

# --- ИЗМЕНЕНИЕ В ГЛАВНОЙ ФУНКЦИИ ---
async def enrich_phrase(keyword: str, lang_code: str, target_lang: str = 'ru') -> dict | None:
    logging.info(f"--- НАЧАЛО ОБОГАЩЕНИЯ (AI) для '{keyword}' [{lang_code}] ---")
    try:
        # Нам нужен полный язык для промпта, например 'english', 'portuguese'
        lang_map = {'en': 'english', 'ru': 'russian', 'es': 'spanish', 'pt': 'portuguese'}
        full_language_name = lang_map.get(lang_code, lang_code)

        gathered_results = await asyncio.gather(
            get_translation(keyword, from_lang=lang_code, to_lang=target_lang),
            find_image_for_keyword(keyword),
            # --- ЗАМЕНА ЗДЕСЬ ---
            generate_examples_with_ai(keyword, full_language_name),
            generate_audio(keyword, lang_code, "keyword")
        )
    except Exception as e:
        logging.error(f"Критическая ошибка во время asyncio.gather: {e}")
        return None

    translation, image_path, examples, keyword_audio_path = gathered_results
    
    enriched_data = {
        'keyword': keyword,
        'translation': translation,
        'examples': examples,
        'image_path': image_path,
        'audio_path': keyword_audio_path,
    }
    
    logging.info(f"--- КОНЕЦ ОБОГАЩЕНИЯ для '{keyword}'. Найдено {len(examples) if examples else 0} примеров. ---")
    return enriched_data