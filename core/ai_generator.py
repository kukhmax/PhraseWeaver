# Файл: core/ai_generator.py
import os
import google.generativeai as genai
import logging
import json

try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    logging.info("Модель Google Gemini успешно настроена.")
except KeyError:
    # ... (обработка ошибок без изменений) ...
    logging.error("КРИТИЧЕСКАЯ ОШИБКА: Переменная окружения GOOGLE_API_KEY не установлена!")
    model = None
except Exception as e:
    logging.error(f"Ошибка конфигурации Gemini API: {e}")
    model = None

# --- ИЗМЕНЕНИЕ: Улучшаем наш промпт ---
PROMPT_TEMPLATE = """
Твоя задача - помочь в изучении языков.
Для слова или фразы "{keyword}" на языке "{language}":

1.  Придумай одно или два ключевых слова на английском языке для поиска картинки, которая лучше всего визуально ассоциируется с "{keyword}". Назови это поле "image_query".
2.  Создай 5 реалистичных примеров предложений со словом "{keyword}". Используй разные грамматические формы.
3.  Для каждого предложения предоставь точный перевод на русский язык.

Критически важно: верни ответ ТОЛЬКО в виде валидного JSON-объекта, без каких-либо других слов или форматирования.

Пример формата:
{{
  "image_query": "home cottage peaceful",
  "examples": [
    {{"original": "Пример предложения...", "translation": "Его перевод..."}},
    {{"original": "Второй пример...", "translation": "Второй перевод..."}}
  ]
}}
"""

async def generate_examples_with_ai(keyword: str, language: str) -> dict | None:
    if not model: return None

    prompt = PROMPT_TEMPLATE.format(keyword=keyword, language=language)
    logging.info(f"Отправка AI-запроса для '{keyword}'...")

    try:
        response = await model.generate_content_async(prompt)
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        # Теперь мы ожидаем не список, а словарь
        data = json.loads(raw_text)
        logging.info(f"AI успешно сгенерировал данные для '{keyword}'.")
        return data # Возвращаем весь словарь {"image_query": ..., "examples": [...]}

    except Exception as e:
        logging.error(f"Ошибка при работе с AI: {e}")
        return None