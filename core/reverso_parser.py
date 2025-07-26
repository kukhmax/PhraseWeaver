# Файл: core/reverso_parser.py

import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import logging

# Настройка логирования для отладки
logging.basicConfig(level=logging.INFO, format='%(asctime)s - REVERSO - %(levelname)s - %(message)s')

# Заголовок, чтобы притвориться браузером и избежать блокировки
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

async def find_examples_on_reverso(phrase: str, lang_from: str, lang_to: str, limit: int = 7) -> list[dict]:
    """
    Находит примеры использования фразы на Reverso Context.
    Возвращает список словарей: [{'original': ..., 'translation': ...}, ...]
    """
    # Преобразуем языки в формат, понятный Reverso (например, 'en' -> 'english')
    # Это пример, для реального приложения нужен будет полный словарь соответствий
    lang_map = {'en': 'english', 'ru': 'russian', 'es': 'spanish', 'pt': 'portuguese'}
    lang_from_full = lang_map.get(lang_from, lang_from)
    lang_to_full = lang_map.get(lang_to, lang_to)

    # Формируем URL для поиска
    encoded_phrase = quote_plus(phrase)
    url = f"https://context.reverso.net/translation/{lang_from_full}-{lang_to_full}/{encoded_phrase}"
    logging.info(f"Запрашиваю URL: {url}")

    examples = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.error(f"Reverso ответил статусом {response.status}")
                    return []
                
                html_text = await response.text()
                soup = BeautifulSoup(html_text, "html.parser")
                
                # Ищем все блоки с примерами
                example_divs = soup.find_all('div', class_='example', limit=limit * 2) # Берем с запасом

                for div in example_divs:
                    # Находим оригинальную фразу и ее перевод
                    original_span = div.find('div', class_='src').find('span', class_='text')
                    translation_span = div.find('div', class_='trg').find('span', class_='text')

                    if original_span and translation_span:
                        examples.append({
                            'original': original_span.get_text(strip=True),
                            'translation': translation_span.get_text(strip=True)
                        })
                    
                    if len(examples) >= limit:
                        break # Останавливаемся, когда набрали достаточно примеров

    except Exception as e:
        logging.error(f"Ошибка при парсинге Reverso: {e}")

    logging.info(f"Найдено {len(examples)} примеров.")
    return examples