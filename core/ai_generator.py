# Файл: core/ai_generator.py (ФИНАЛЬНАЯ ВЕРСИЯ ПРОМПТА)

import os
import google.generativeai as genai
import logging
import json

try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    logging.info("Модель Google Gemini успешно настроена.")
except KeyError:
    logging.error("КРИТИЧЕСКАЯ ОШИБКА: Переменная окружения GOOGLE_API_KEY не установлена!")
    model = None
except Exception as e:
    logging.error(f"Ошибка конфигурации Gemini API: {e}")
    model = None

# --- ИЗМЕНЕНИЕ: Улучшаем наш промпт, просим выделять слова ---
PROMPT_TEMPLATE = """
Твоя задача - помочь в изучении языков.
Для слова или фразы "{keyword}" на языке "{language}":

1.  Придумай одно-два ключевых слова на английском для поиска картинки, которая лучше всего ассоциируется с "{keyword}". Назови это поле "image_query".
2.  Создай 5 реалистичных примеров предложений. Используй разные грамматические формы слова "{keyword}".
3.  Для каждого предложения предоставь точный перевод на русский язык.
4.  Критически важно: в каждом оригинальном предложении найди слово "{keyword}" (в любой его форме) и оберни его в HTML-теги <b> и </b>.

Верни ответ ТОЛЬКО в виде валидного JSON-объекта, без каких-либо других слов или форматирования.

Пример формата:
{{
  "image_query": "walking home sunset",
  "examples": [
    {{"original": "Eu estou <b>indo</b> para casa.", "translation": "Я иду домой."}},
    {{"original": "Eles <b>foram</b> para a praia.", "translation": "Они пошли на пляж."}}
  ]
}}
"""

async def generate_examples_with_ai(keyword: str, language: str) -> dict | None:
    # ... (остальная часть файла остается без изменений) ...
    if not model: return None
    prompt = PROMPT_TEMPLATE.format(keyword=keyword, language=language)
    logging.info(f"Отправка AI-запроса для '{keyword}'...")
    try:
        response = await model.generate_content_async(prompt)
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw_text)
        logging.info(f"AI успешно сгенерировал данные для '{keyword}'.")
        return data
    except Exception as e:
        logging.error(f"Ошибка при работе с AI: {e}")
        return None