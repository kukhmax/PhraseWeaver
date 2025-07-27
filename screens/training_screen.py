# (ПОЛНОСТЬЮ НОВАЯ ЛОГИКА)
import json
import random
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

# Нам понадобится наш SRS-калькулятор, но мы его пока не импортируем,
# так как в этой версии он может быть не готов.
# from core.srs import calculate_next_due_date

class TrainingScreen(MDScreen):
    # --- Свойства для управления сессией ---
    deck_id = None
    all_cards = []          # Полный список карточек на сессию
    current_card = None     # Карточка, которую видит пользователь сейчас
    _current_mode = None    # Режим работы главной кнопки ('show_answer' или 'check_answer')

    def on_enter(self, *args):
        """Вызывается при входе на экран. Запускает новую сессию."""
        self.load_session_cards()
        self.show_next_card()

    def load_session_cards(self):
        """Загружает и перемешивает карточки для тренировки."""
        app = MDApp.get_running_app()
        # В self.manager.current_deck_id мы сохранили id при переходе с главного экрана
        self.deck_id = self.manager.current_deck_id 
        # TODO: Заменить на реальный вызов из БД
        # self.all_cards = app.db_manager.get_cards_for_review(self.deck_id)
        
        # --- ВРЕМЕННАЯ ЗАГЛУШКА ДЛЯ ТЕСТИРОВАНИЯ ---
        # Мы создадим несколько "фальшивых" карточек, чтобы протестировать все 3 режима
        self.all_cards = [
            {'id': 1, 'card_type': 'direct_recognition', 'front': '{"text": "I am going home", "image": "assets/placeholder.png", "audio": "path/to/audio1.mp3"}', 'back': 'Я иду домой'},
            {'id': 2, 'card_type': 'reverse_recall', 'front': '{"text": "Собака лает", "image": "assets/placeholder.png"}', 'back': 'The dog barks'},
            {'id': 3, 'card_type': 'context_cloze', 'front': '{"text": "The cat sits on the ______.", "image": "assets/placeholder.png", "audio": "path/to/audio3.mp3"}', 'back': 'mat'},
        ]
        # --- КОНЕЦ ЗАГЛУШКИ ---
        
        random.shuffle(self.all_cards)

    # --- Главный Метод-Дирижер ---
    def show_next_card(self):
        """
        Главный метод, который управляет отображением следующей карточки.
        """
        # Сбрасываем UI в исходное состояние
        self._reset_ui()

        if not self.all_cards:
            self.end_training()
            return

        self.current_card = self.all_cards.pop(0)
        card_type = self.current_card['card_type']
        
        try:
            front_data = json.loads(self.current_card['front'])
        except (json.JSONDecodeError, TypeError):
            # Если в поле front не JSON, а простой текст (для старых карточек)
            front_data = {'text': self.current_card['front']}
            
        # Определяем, какой режим тренировки использовать
        if card_type == 'direct_recognition':
            self._setup_direct_recognition_card(front_data)
        elif card_type == 'reverse_recall':
            self._setup_reverse_recall_card(front_data)
        elif card_type == 'context_cloze':
            self._setup_context_cloze_card(front_data)
        
        # Обновляем прогресс-бар
        total = len(self.all_cards) + 1 # +1, т.к. мы уже взяли одну карточку
        progress = (total - len(self.all_cards)) / total * 100
        self.ids.progress_bar.value = progress

    # --- Вспомогательные Методы для Настройки UI ---
    def _setup_direct_recognition_card(self, data):
        """Настраивает UI для "Классической карточки"."""
        self.ids.card_image.source = data.get('image', 'assets/placeholder.png')
        self.ids.question_label.text = data.get('text', '')
        self.ids.action_button.text = "Показать ответ"
        self._current_mode = 'show_answer'

    def _setup_reverse_recall_card(self, data):
        """Настраивает UI для "Перевода-Спринта"."""
        self.ids.card_image.source = data.get('image', 'assets/placeholder.png')
        self.ids.question_label.text = data.get('text', '') # Здесь будет перевод
        self._show_input_field(True)
        self.ids.action_button.text = "Проверить"
        self._current_mode = 'check_answer'

    def _setup_context_cloze_card(self, data):
        """Настраивает UI для "Понимания в Контексте"."""
        self.ids.card_image.source = data.get('image', 'assets/placeholder.png')
        self.ids.question_label.text = data.get('text', '') # Здесь будет фраза с пропуском
        self._show_input_field(True)
        self.ids.action_button.text = "Проверить"
        self._current_mode = 'check_answer'

    # --- Обработчики Действий Пользователя ---
    def handle_main_action(self):
        """Обрабатывает нажатие на главную кнопку ('Показать ответ' / 'Проверить')."""
        if self._current_mode == 'show_answer':
            self.show_correct_answer()
        elif self._current_mode == 'check_answer':
            self.check_typed_answer()
    
    def check_typed_answer(self):
        """Сравнивает введенный пользователем текст с правильным ответом."""
        user_answer = self.ids.answer_input.text.strip()
        correct_answer = self.current_card['back']
        
        # Простое сравнение без учета регистра
        if user_answer.lower() == correct_answer.lower():
            # Правильно! Показываем зеленый цвет
            self.ids.answer_input.text_color_normal = MDApp.get_running_app().theme_cls.primary_color
        else:
            # Неправильно! Показываем красный цвет и правильный ответ
            self.ids.answer_input.text_color_normal = MDApp.get_running_app().theme_cls.error_color
            self.ids.correct_answer_label.text = f"Правильно: {correct_answer}"
            self.ids.correct_answer_label.height = self.ids.correct_answer_label.texture_size[1]
            
        self._show_srs_buttons(True)
        
    def show_correct_answer(self):
        """Просто показывает 'спинку' карточки."""
        self.ids.correct_answer_label.text = self.current_card['back']
        self.ids.correct_answer_label.height = self.ids.correct_answer_label.texture_size[1]
        self._show_srs_buttons(True)

    def play_audio(self):
        """Проигрывает аудиофайл, связанный с карточкой."""
        try:
            front_data = json.loads(self.current_card['front'])
            audio_path = front_data.get('audio')
            if audio_path:
                sound = SoundLoader.load(audio_path)
                if sound:
                    sound.play()
        except Exception as e:
            print(f"Ошибка проигрывания аудио: {e}")

    def evaluate_answer(self, quality: str):
        """Обрабатывает оценку SRS и переходит к следующей карточке."""
        print(f"Карточка {self.current_card['id']} оценена как '{quality}'")
        # --- ЗДЕСЬ БУДЕТ ЛОГИКА SRS ---
        # new_srs_data = calculate_next_due_date(...)
        # app.db_manager.update_card_srs(...)
        # -----------------------------
        self.show_next_card()

    def end_training(self):
        """Завершает тренировку."""
        self.ids.question_label.text = "Тренировка завершена!"
        self.ids.card_image.source = ''
        self.ids.action_button.disabled = True
        # Возвращаемся на главный экран через 2 секунды
        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'deck_list'), 2)
        
    # --- Вспомогательные Методы для Управления UI ---
    def _reset_ui(self):
        """Сбрасывает UI к начальному состоянию перед показом новой карточки."""
        self.ids.srs_buttons.opacity = 0
        self.ids.srs_buttons.disabled = True
        self.ids.action_button.disabled = False
        self.ids.correct_answer_label.text = ""
        self.ids.correct_answer_label.height = 0
        self.ids.answer_input.text = ""
        self.ids.answer_input.text_color_normal = MDApp.get_running_app().theme_cls.text_color
        self._show_input_field(False)
    
    def _show_input_field(self, show: bool):
        """Показывает или прячет поле для ввода текста."""
        if show:
            self.ids.answer_input.height = "48dp"
            self.ids.answer_input.opacity = 1
            self.ids.answer_input.disabled = False
        else:
            self.ids.answer_input.height = 0
            self.ids.answer_input.opacity = 0
            self.ids.answer_input.disabled = True
            
    def _show_srs_buttons(self, show: bool):
        """Показывает или прячет кнопки SRS и главную кнопку."""
        if show:
            self.ids.srs_buttons.opacity = 1
            self.ids.srs_buttons.disabled = False
            self.ids.action_button.disabled = True
        else:
            self.ids.srs_buttons.opacity = 0
            self.ids.srs_buttons.disabled = True