import asyncio
import logging
import os
import re
from pathlib import Path

import aiohttp
from googletrans import Translator
from bs4 import BeautifulSoup
from duckduckgo_search import AsyncDDGS
from gtts import gTTS

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Константы ---
# Целевой язык для перевода и озвучки. В будущем можно вынести в настройки.
TARGET_LANGUAGE = 'ru' 
# Папка для сохранения аудиофайлов
AUDIO_DIR = Path("assets/audio")


async def get_translation(text: str, to_language: str = TARGET_LANGUAGE) -> str | None:
    """Получает перевод текста с помощью библиотеки googletrans."""
    logging.info(f"Получение перевода для: '{text}'")
    try:
        # googletrans - синхронная библиотека, ее нужно запускать в executor'е,
        # чтобы не блокировать асинхронный цикл.
        loop = asyncio.get_running_loop()
        
        def translate_sync():
            translator = Translator()
            # Указываем язык источника 'en' и язык назначения.
            translation_result = translator.translate(text, src='en', dest=to_language)
            return translation_result.text

        translated_text = await loop.run_in_executor(None, translate_sync)
        
        logging.info(f"Перевод получен: '{translated_text}'")
        return translated_text
    except Exception as e:
        logging.error(f"Ошибка перевода: {e}")
        return None


async def find_usage_examples(phrase: str, num_examples: int = 5) -> list[str]:
    """Ищет реальные примеры использования фразы в интернете."""
    logging.info(f"Поиск примеров для: '{phrase}'")
    examples = []
    # Ищем предложения, содержащие нашу фразу. Двойные кавычки важны для точного поиска.
    query = f'"{phrase}"'
    
    # 
    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
    #
    search_results = []
    try:
        async with AsyncDDGS() as ddgs:
            # .text() в новых версиях - это обычная корутина, возвращающая список.
            # Мы ее просто `await`им.
            search_results = await ddgs.text(query, max_results=num_examples * 2)
    except Exception as e:
        logging.error(f"Ошибка при поиске в DuckDuckGo: {e}")
        return [] # Возвращаем пустой список, если поиск упал

    if not search_results:
        logging.warning(f"Примеры для '{phrase}' не найдены.")
        return []

    # Остальной код функции не меняется...
    async with aiohttp.ClientSession() as session:
        for result in search_results:
            try:
                # В v5 ключ для URL - 'href', а в v4 был 'url'. Делаем универсально.
                url = result.get('href') 
                if not url:
                    continue
                
                async with session.get(url, timeout=5) as response:
                    if response.status != 200:
                        continue
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    # Ищем текст внутри тегов <p> - самый частый контейнер для предложений
                    paragraphs = soup.find_all('p')
                    for p in paragraphs:
                        text = p.get_text()
                        # Используем regex для поиска предложений, содержащих нашу фразу.
                        # re.IGNORECASE делает поиск нечувствительным к регистру.
                        sentences = re.findall(f'[^.!?]*{re.escape(phrase)}[^.!?]*[.!?]', text, re.IGNORECASE)
                        for sentence in sentences:
                            clean_sentence = sentence.strip()
                            if len(clean_sentence.split()) > 4: # Отсеиваем слишком короткие
                                examples.append(clean_sentence)
                                if len(examples) >= num_examples:
                                    logging.info(f"Найдено {len(examples)} примеров.")
                                    return examples
            except Exception as e:
                logging.warning(f"Не удалось обработать URL {url}: {e}")

    logging.info(f"Найдено {len(examples)} примеров.")
    return examples


async def generate_audio(text: str, lang: str, filename: str) -> str | None:
    """Генерирует аудиофайл из текста и сохраняет его."""
    logging.info(f"Генерация аудио для: '{text}'")
    try:
        # gTTS - синхронная библиотека, запускаем в executor'е
        loop = asyncio.get_running_loop()
        tts = await loop.run_in_executor(None, lambda: gTTS(text=text, lang=lang, slow=False))
        
        output_path = AUDIO_DIR / f"{filename}.mp3"
        await loop.run_in_executor(None, tts.save, output_path)
        
        logging.info(f"Аудио сохранено в: {output_path}")
        return str(output_path)
    except Exception as e:
        logging.error(f"Ошибка генерации аудио: {e}")
        return None


async def enrich_phrase(phrase: str) -> dict:
    """
    Главная оркестрирующая функция. Запускает все процессы обогащения.
    """
    logging.info(f"--- Начало процесса обогащения для фразы: '{phrase}' ---")
    # Создаем уникальное имя файла на основе хэша фразы, чтобы избежать конфликтов
    safe_filename = abs(hash(phrase))
    
    # Запускаем задачи перевода и поиска примеров параллельно
    translation_task = asyncio.create_task(get_translation(phrase))
    examples_task = asyncio.create_task(find_usage_examples(phrase))

    # Ждем завершения обеих задач
    translation = await translation_task
    examples = await examples_task

    # Теперь генерируем аудио. Мы можем это делать параллельно для всех фраз.
    audio_tasks = []
    # 1. Аудио для ключевой фразы
    audio_tasks.append(asyncio.create_task(
        generate_audio(phrase, 'en', f"keyword_{safe_filename}")
    ))
    # 2. Аудио для перевода (если он есть)
    if translation:
        audio_tasks.append(asyncio.create_task(
            generate_audio(translation, TARGET_LANGUAGE, f"translation_{safe_filename}")
        ))
    # 3. Аудио для примеров
    for i, example in enumerate(examples):
        audio_tasks.append(asyncio.create_task(
            generate_audio(example, 'en', f"example_{safe_filename}_{i}")
        ))
    
    audio_results = await asyncio.gather(*audio_tasks)

    # Собираем результаты в словарь
    result = {
        "keyword_phrase": phrase,
        "translation": translation,
        "examples": examples,
        "audio_paths": {
            "keyword": audio_results[0],
            "translation": audio_results[1] if translation else None,
            "examples": audio_results[2:] if translation else audio_results[1:]
        }
    }
    logging.info(f"--- Процесс обогащения для '{phrase}' завершен ---")
    return result

# --- Тестовый запуск ---
async def main_test():
    """Функция для ручного тестирования модуля."""
    phrase_to_enrich = "a blessing in disguise"
    enriched_data = await enrich_phrase(phrase_to_enrich)
    import json
    print(json.dumps(enriched_data, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    # Чтобы запустить этот файл напрямую для теста:
    # python core/enrichment.py
    asyncio.run(main_test())