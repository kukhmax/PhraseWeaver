# Файл: core/enrichment.py (ФИНАЛЬНАЯ ВЕРСИЯ v4)

import asyncio, logging, os, hashlib, aiohttp
from pathlib import Path
from core.ai_generator import generate_examples_with_ai
from core.image_finder import find_image_via_api
from gtts import gTTS
from googletrans import Translator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - ENRICH - %(levelname)s - %(message)s')
AUDIO_DIR, IMAGE_DIR = Path("assets/audio"), Path("assets/images")

def ensure_dir_exists(*dirs): [d.mkdir(parents=True, exist_ok=True) for d in dirs if not d.exists()]
ensure_dir_exists(AUDIO_DIR, IMAGE_DIR)

async def get_translation(text: str, from_lang: str, to_lang: str) -> str | None:
    try:
        def translate_sync():
            return Translator().translate(text, src=from_lang, dest=to_lang).text
        return await asyncio.get_running_loop().run_in_executor(None, translate_sync)
    except Exception as e:
        logging.error(f"Ошибка перевода: {e}")
        return None

async def generate_audio(text: str, lang: str, prefix: str):
    try:
        path = AUDIO_DIR / f"{prefix}_{hashlib.md5(text.encode()).hexdigest()[:8]}.mp3"
        if path.exists(): return str(path)
        tts = await asyncio.get_running_loop().run_in_executor(None, lambda: gTTS(text=text, lang=lang, slow=False))
        await asyncio.get_running_loop().run_in_executor(None, tts.save, str(path))
        return str(path)
    except Exception as e:
        logging.error(f"Ошибка генерации аудио: {e}")
        return None

async def download_and_save_image(image_url: str, query: str) -> str | None:
    if not image_url: return None
    try:
        path = IMAGE_DIR / f"{hashlib.md5(query.encode()).hexdigest()}{Path(image_url.split('?')[0]).suffix or '.jpg'}"
        async with aiohttp.ClientSession() as s, s.get(image_url) as r:
            if r.status == 200:
                with open(path, 'wb') as f: f.write(await r.read())
                logging.info(f"Картинка сохранена: {path}")
                return str(path)
    except Exception as e:
        logging.error(f"Ошибка скачивания картинки: {e}")
    return None

async def enrich_phrase(keyword: str, lang_code: str, target_lang: str = 'ru') -> dict | None:
    logging.info(f"--- НАЧАЛО ОБОГАЩЕНИЯ (API V3) для '{keyword}' ---")
    lang_map = {'en': 'english', 'ru': 'russian', 'es': 'spanish', 'pt': 'portuguese'}
    full_language_name = lang_map.get(lang_code, lang_code)
    
    ai_data = await generate_examples_with_ai(keyword, full_language_name)
    if not ai_data: return None

    image_query_original = ai_data.get("image_query", keyword)
    examples = ai_data.get("examples", [])

    # --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: ПЕРЕВОДИМ ЗАПРОС НА АНГЛИЙСКИЙ ---
    english_image_query = image_query_original
    if lang_code != 'en':
        logging.info(f"Перевожу запрос для картинки '{image_query_original}' на английский...")
        translated_query = await get_translation(image_query_original, from_lang=lang_code, to_lang='en')
        if translated_query:
            english_image_query = translated_query
            logging.info(f"Запрос для картинки стал: '{english_image_query}'")

    # Используем английский запрос для поиска по API
    image_url_from_api = await find_image_via_api(english_image_query)

    gathered_results = await asyncio.gather(
        get_translation(keyword, from_lang=lang_code, to_lang=target_lang),
        # Скачиваем, используя английский запрос для создания имени файла
        download_and_save_image(image_url_from_api, english_image_query),
        generate_audio(keyword, lang_code, "keyword")
    )
    
    translation, image_path, keyword_audio_path = gathered_results
    
    return {
        'keyword': keyword, 'translation': translation,
        'examples': examples, 'image_path': image_path,
        'audio_path': keyword_audio_path,
    }