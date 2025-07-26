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
    logging.error("Перед запуском выполните в терминале: export GOOGLE_API_KEY='ВАШ_КЛЮЧ'")
    model = None
except Exception as e:
    logging.error(f"Ошибка конфигурации Gemini API: {e}")
    model = None

PROMPT_TEMPLATE = """
Твоя задача - помочь в изучении языков. 
Создай 5 реалистичных примеров предложений на языке "{language}" со словом или фразой "{keyword}".
Используй разные грамматические формы этого слова, если это возможно (разные времена, падежи, спряжения).
Для каждого предложения предоставь точный перевод на русский язык.

Критически важно: верни ответ ТОЛЬКО в виде валидного JSON-массива объектов, без каких-либо других слов, пояснений или markdown-форматирования.

Пример формата:
[
  {{"original": "Пример предложения на заданном языке...", "translation": "Его перевод на русский..."}},
  {{"original": "Второй пример...", "translation": "Второй перевод..."}}
]
"""

async def generate_examples_with_ai(keyword: str, language: str) -> list[dict]:
    if not model:
        logging.error("Модель AI не инициализирована. Примеры не будут сгенерированы.")
        return []

    prompt = PROMPT_TEMPLATE.format(keyword=keyword, language=language)
    print("\n--- DEBUG: Промпт для AI ---\n", prompt, "\n--------------------------\n")

    try:
        response = await model.generate_content_async(prompt)
        raw_text = response.text.strip()
        print(f"--- DEBUG: СЫРОЙ ОТВЕТ ОТ AI ---\n{raw_text}\n--------------------------\n")
        
        cleaned_response = raw_text.replace("```json", "").replace("```", "").strip()

        examples = json.loads(cleaned_response)
        logging.info(f"AI успешно сгенерировал и распарсил {len(examples)} примеров.")
        return examples

    except json.JSONDecodeError as e:
        print(f"--- DEBUG: ОШИБКА ПАРСИНГА JSON ---\n{e}\n--------------------------\n")
        logging.error(f"Не удалось распарсить JSON от AI. Ответ был: {raw_text}")
        return []
    except Exception as e:
        print(f"--- DEBUG: КРИТИЧЕСКАЯ ОШИБКА В AI ---\n{e}\n--------------------------\n")
        logging.error(f"Неизвестная ошибка при работе с AI: {e}")
        return []