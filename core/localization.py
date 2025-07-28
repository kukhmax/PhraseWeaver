from kivymd.app import MDApp

TRANSLATIONS = {
    'ru': {
        # Общие
        'settings': 'Настройки',
        'cancel': 'Отмена',
        'create': 'Создать',

        # DeckList Screen (Главный экран)
        'deck_list_title': 'PhraseWeaver',
        'create_deck': 'Создать колоду',
        'add_card': 'Добавить карточку',
        'total_cards': 'Всего',
        'due_cards': 'К повторению',
        'no_decks': 'Колод пока нет. Создайте первую!',
        'no_cards_for_review': 'В этой колоде нет карточек для повторения.',
        
        # Create Deck Dialog (Диалог создания колоды)
        'create_new_deck': 'Создать новую колоду',
        'deck_name': 'Название колоды',
        'select_language': 'Выберите язык',

        # Creation Screen (Экран создания)
        'create_card_title': 'Создать карточку',
        'full_sentence_hint': 'Полное предложение (контекст)',
        'keyword_hint': 'Ключевая фраза',
        'enrich_button': 'Обогатить ✨',
        'no_keyword_error': 'Ключевая фраза не может быть пустой!',
        'no_examples_found': "Не удалось найти примеры для '{keyword}'",

        # Curation Screen (Экран выбора)
        'curation_title': 'Выберите лучшее',
        'found_examples': 'Найденные примеры:',
        'add_selected_button': 'Добавить выбранное',
        'saving_cards_toast': "Сохранение карточек... Это может занять несколько секунд.",
        'no_examples_to_save': "Нет примеров для сохранения!",
        'cards_saved_toast': "Успешно добавлено {count} новых карточек!",

        # Training Screen (Экран тренировки)
        'training_title': 'Тренировка',
        'your_answer_hint': 'Ваш ответ...',
        'show_answer_button': 'Показать ответ',
        'check_answer_button': 'Проверить',
        'correct_answer_is': 'Правильно: {answer}',
        'training_complete': 'Тренировка завершена!',
        'btn_again': 'Снова',
        'btn_good': 'Хорошо',
        'btn_easy': 'Легко',

        # Stats Screen (Экран статистики)
        'stats_title': 'Ваш Прогресс',
        'learned_cards': 'Карточек выучено',
        'streak': 'Ударная серия',
        'activity_chart_title': 'Активность за последнюю неделю',
        'chart_x_label': 'Дата',
        'chart_y_label': 'Повторения',

        # Settings Screen (Экран настроек)
        'settings_title': 'Настройки',
        'language_settings': 'Языковые настройки',
        'translate_to': 'Я перевожу на',
        'select_target_language': 'Выберите язык для перевода',
        'interface_language': 'Язык интерфейса',
        'select_ui_language': 'Выберите язык интерфейса',
        'language_name': 'Русский',
    },
    'en': {
        # General
        'settings': 'Settings',
        'cancel': 'Cancel',
        'create': 'Create',

        # DeckList Screen
        'deck_list_title': 'PhraseWeaver',
        'create_deck': 'Create Deck',
        'add_card': 'Add Card',
        'total_cards': 'Total',
        'due_cards': 'To Review',
        'no_decks': 'No decks yet. Create your first one!',
        'no_cards_for_review': 'No cards to review in this deck.',

        # Create Deck Dialog
        'create_new_deck': 'Create a new deck',
        'deck_name': 'Deck Name',
        'select_language': 'Select language',
        
        # Creation Screen
        'create_card_title': 'Create Card',
        'full_sentence_hint': 'Full sentence (context)',
        'keyword_hint': 'Keyword or phrase',
        'enrich_button': 'Enrich ✨',
        'no_keyword_error': 'Keyword cannot be empty!',
        'no_examples_found': "Could not find examples for '{keyword}'",

        # Curation Screen
        'curation_title': 'Choose the Best',
        'found_examples': 'Found Examples:',
        'add_selected_button': 'Add Selected',
        'saving_cards_toast': "Saving cards... This may take a few seconds.",
        'no_examples_to_save': "No examples to save!",
        'cards_saved_toast': "Successfully added {count} new cards!",
        
        # Training Screen
        'training_title': 'Training',
        'your_answer_hint': 'Your answer...',
        'show_answer_button': 'Show Answer',
        'check_answer_button': 'Check',
        'correct_answer_is': 'Correct: {answer}',
        'training_complete': 'Training complete!',
        'btn_again': 'Again',
        'btn_good': 'Good',
        'btn_easy': 'Easy',
        
        # Stats Screen
        'stats_title': 'Your Progress',
        'learned_cards': 'Cards Learned',
        'streak': 'Current Streak',
        'activity_chart_title': 'Activity in the last week',
        'chart_x_label': 'Date',
        'chart_y_label': 'Reviews',
        
        # Settings Screen
        'settings_title': 'Settings',
        'language_settings': 'Language Settings',
        'translate_to': 'I translate to',
        'select_target_language': 'Select target language',
        'interface_language': 'Interface Language',
        'select_ui_language': 'Select Interface Language',
        'language_name': 'English',
    }
}


class Translator:
    def __init__(self, language='ru'): # По умолчанию русский
        self.language = language
        self.lexicon = TRANSLATIONS.get(language, TRANSLATIONS['en'])

    def set_language(self, language_code):
        self.language = language_code
        self.lexicon = TRANSLATIONS.get(language_code, TRANSLATIONS.get('en', {}))

    def t(self, key, **kwargs):
        string = self.lexicon.get(key, key)
        try:
            return string.format(**kwargs) if kwargs else string
        except KeyError: # Защита от неправильного форматирования
            return string

# Создаем ОДИН глобальный экземпляр, который будет жить в приложении
translator = Translator()