# Файл: core/enrichment.py

import asyncio
import logging
import os
import aiohttp
import hashlib
from pathlib import Path

# Импортируем наши новые парсеры и поисковики
from .reverso_parser import find_examples_on_reverso
from duckduckgo_search import AsyncDDGS
from gtts import gTTS
from googletrans import Translator

# --- Настройка модулей ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - ENRICH - %(levelname)s - %(message)s')
AUDIO_DIR = Path("assets/audio")
IMAGE_DIR = Path("assets/images")

# --- Утилиты ---
def ensure_dir_exists(*dirs):
    """Убеждается, что все перечисленные директории существуют."""
    for dir_path in dirs:
        if not dir_path.exists():
            logging.info(f"Создаю директорию: {dir_path}")
            dir_path.mkdir(parents=True, exist_ok=True)

# Вызываем один раз при загрузке модуля
ensure_dir_exists(AUDIO_DIR, IMAGE_DIR)


# --- Функции-исполнители ---

async def get_translation(text: str, from_lang: str, to_lang: str = 'ru') -> str | None:
    """Получает перевод текста. (Адаптированная твоя функция)."""
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
    """
    Находит, скачивает и сохраняет картинку для ключевого слова.
    Возвращает локальный путь к картинке или None.
    """
    logging.info(f"Поиск картинки для '{keyword}'...")
    try:
        async with AsyncDDGS() as ddgs:
            # Ищем картинки и берем первую
            results = [r async for r in ddgs.images(keyword, max_results=1)]
            if not results:
                logging.warning("Картинки не найдены.")
                return None
            
            image_url = results[0].get('image')
            if not image_url: return None

            logging.info(f"Найдена картинка: {image_url}")
            # Создаем уникальное имя файла, чтобы избежать конфликтов и ошибок
            file_hash = hashlib.md5(keyword.encode()).hexdigest()
            extension = os.path.splitext(image_url.split('?')[0])[-1] or '.jpg'
            image_path = IMAGE_DIR / f"{file_hash}{extension}"

            # Скачиваем асинхронно
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
    """Генерирует аудиофайл из текста и сохраняет его."""
    logging.info(f"Генерация аудио для: '{text}' ({lang})")
    try:
        # Уникализируем имя файла
        file_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        output_path = AUDIO_DIR / f"{filename_prefix}_{file_hash}.mp3"

        # Если файл уже существует, не будем его генерировать заново
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

# --- Главная функция-оркестратор ---

async def enrich_phrase(keyword: str, lang_code: str, target_lang: str = 'ru') -> dict | None:
    """
    Главная оркестрирующая функция. Запускает все процессы обогащения параллельно.
    """
    logging.info(f"--- НАЧАЛО ОБОГАЩЕНИЯ для '{keyword}' [{lang_code}] ---")
    
    # Запускаем все тяжелые сетевые и файловые операции параллельно
    try:
        gathered_results = await asyncio.gather(
            get_translation(keyword, from_lang=lang_code, to_lang=target_lang),
            find_image_for_keyword(keyword),
            find_examples_on_reverso(keyword, lang_from=lang_code, lang_to=target_lang),
            generate_audio(keyword, lang_code, "keyword")
        )
    except Exception as e:
        logging.error(f"Критическая ошибка во время asyncio.gather: {e}")
        return None

    # Распаковываем результаты для удобства
    translation, image_path, examples, keyword_audio_path = gathered_results
    
    # Собираем финальный словарь с результатами
    enriched_data = {
        'keyword': keyword,
        'translation': translation,
        'examples': examples,  # Это уже список словарей [{'original': ..., 'translation': ...}]
        'image_path': image_path,
        'audio_path': keyword_audio_path,
    }
    
    logging.info(f"--- КОНЕЦ ОБОГАЩЕНИЯ для '{keyword}'. Найдено {len(examples)} примеров. ---")
    return enriched_data

# --- Тестовый запуск ---
async def main_test():
    """Функция для ручного тестирования модуля."""
    # Убедимся, что файл парсера существует и доступен
    try:
        from core.reverso_parser import find_examples_on_reverso
        logging.info("Парсер Reverso успешно импортирован.")
    except ImportError:
        logging.error("Не удалось импортировать reverso_parser.py. Убедитесь, что файл находится в папке core.")
        return
        
    phrase_to_enrich = "a blessing in disguise"
    enriched_data = await enrich_phrase(phrase_to_enrich, 'en')
    import json
    print("\n--- РЕЗУЛЬТАТ ОБОГАЩЕНИЯ ---")
    print(json.dumps(enriched_data, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    # Чтобы запустить этот файл напрямую для теста:
    # python -m core.enrichment
    # Важно запускать с флагом -m, чтобы работали относительные импорты
    asyncio.run(main_test())