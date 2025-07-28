import json, random
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

from core.srs import calculate_next_due_date


class TrainingScreen(MDScreen):
    deck_id=None
    all_cards=[]
    current_card=None
    _current_mode=None
    _session_total=0
    
    def on_enter(self, *args):
        # Добавляем app как свойство для легкого доступа
        self.app = MDApp.get_running_app()
        self.load_session_cards(); self.show_next_card()
    
    def load_session_cards(self):
        self.deck_id = self.manager.current_deck_id
        self.all_cards = self.app.db_manager.get_cards_for_review(self.deck_id)
        self._session_total = len(self.all_cards)
        random.shuffle(self.all_cards)
    
    def show_next_card(self):
        self._reset_ui()
        if not self.all_cards:
            self.end_training()
            return

        self.current_card = self.all_cards.pop(0)
        card_type = self.current_card['card_type']
        
        try:
            front_data = json.loads(self.current_card['front'])
        except (json.JSONDecodeError, TypeError):
            front_data = {'text': self.current_card['front']}
        
        self._setup_card_ui(front_data)

        if card_type == 'direct_recognition':
            self.ids.action_button.text = self.app.translator.t('show_answer_button')
            self._current_mode = 'show_answer'
        elif card_type in ['reverse_recall', 'context_cloze']:
            self._show_input_field(True)
            self.ids.action_button.text = self.app.translator.t('check_answer_button')
            self._current_mode = 'check_answer'
        
        if self._session_total > 0:
            progress = (self._session_total - len(self.all_cards)) / self._session_total * 100
            self.ids.progress_bar.value = progress
    
    def _setup_card_ui(self, data):
        self.ids.question_label.text = data.get('text', '')
        image_path = data.get('image'); self.ids.card_image.source = image_path if image_path else 'assets/tmp/placeholder.png'; self.ids.card_image.reload()
    
    def handle_main_action(self):
        if self._current_mode == 'show_answer': self.show_correct_answer()
        elif self._current_mode == 'check_answer': self.check_typed_answer()

    def check_typed_answer(self):
        """
        Сравнивает введенный пользователем текст с правильным ответом,
        ДАЕТ ВИЗУАЛЬНЫЙ И ЗВУКОВОЙ ОТКЛИК.
        """
        user_answer = self.ids.answer_input.text.strip()
        correct_answer = self.current_card['back']
        
        if user_answer.lower() == correct_answer.lower():
            # Правильно!
            self.ids.answer_input.icon_right = "check-circle"
            self.ids.answer_input.icon_right_color_normal = self.app.theme_cls.primary_color
            # Меняем цвет фона поля ввода на слегка зеленый
            self.ids.answer_input.fill_color_normal = (0.2, 0.8, 0.2, 0.2) 
            # Загружаем и проигрываем звук успеха
            sound = SoundLoader.load('assets/tmp/correct.mp3')

        else:
            # Неправильно!
            self.ids.answer_input.icon_right = "close-circle"
            self.ids.answer_input.icon_right_color_normal = self.app.theme_cls.error_color
            # Меняем цвет фона поля ввода на слегка красный
            self.ids.answer_input.fill_color_normal = (0.8, 0.2, 0.2, 0.2)
            # Показываем правильный ответ
            self.ids.correct_answer_label.text = self.app.translator.t('correct_answer_is', answer=correct_answer)
            # Загружаем и проигрываем звук ошибки
            sound = SoundLoader.load('assets/tmp/wrong.mp3')
        
        if sound:
            sound.play()
            
        self.ids.answer_input.disabled = True # Блокируем поле после ответа
        self._show_srs_buttons(True)
    
    def show_correct_answer(self):
        self.ids.correct_answer_label.text = self.current_card['back']
        self._show_srs_buttons(True)
    
    def play_audio(self):
        try:
            front_data = json.loads(self.current_card['front'])
            if audio_path := front_data.get('audio'):
                if sound := SoundLoader.load(audio_path): sound.play()
        except: pass
    
    def evaluate_answer(self, quality: str):
        app = MDApp.get_running_app()
        card = self.current_card
        
        # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Особая логика для "Снова" ---
        
        # 1. Если ответ "Снова", мы не обновляем SRS в БД сразу.
        #    Мы просто кладем карточку обратно в конец нашей "колоды"
        #    на эту сессию, чтобы повторить ее через несколько минут.
        if quality == 'again':
            self.all_cards.append(card)
            # Перемешиваем конец списка, чтобы повторение было не сразу
            random.shuffle(self.all_cards) 
        
        # 2. Если ответ "Хорошо" или "Легко", мы обновляем SRS в БД.
        else:
            srs_result = calculate_next_due_date(
                repetitions=card['repetitions'],
                interval=card['interval'],
                ease_factor=card['ease_factor'],
                quality=quality
            )
            app.db_manager.update_card_srs(
                card_id=card['id'],
                **srs_result
            )
        
        # 3. В любом случае, переходим к следующей карточке.
        self.show_next_card()
    
    def end_training(self):
        """Завершает тренировку."""
        self.ids.question_label.text = self.app.translator.t('training_complete')
        self.ids.card_image.source = ''
        self.ids.action_button.disabled = True
        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'deck_list'), 2)

    def _reset_ui(self):
        """Сбрасывает UI к начальному состоянию перед показом новой карточки."""
        self.ids.srs_buttons.opacity=0
        self.ids.srs_buttons.disabled = True
        self.ids.action_button.disabled = False
        self.ids.correct_answer_label.text=""
        self.ids.answer_input.text=""; self.ids.answer_input.icon_right=""
        self.ids.answer_input.fill_color_normal = self.app.theme_cls.bg_light
        self._show_input_field(False)
    
    def _show_input_field(self, show: bool):
        if show: self.ids.answer_input.height="48dp"; self.ids.answer_input.opacity=1; self.ids.answer_input.disabled=False
        else: self.ids.answer_input.height=0; self.ids.answer_input.opacity=0; self.ids.answer_input.disabled=True
    
    def _show_srs_buttons(self, show: bool):
        if show: self.ids.srs_buttons.opacity=1; self.ids.srs_buttons.disabled=False; self.ids.action_button.disabled=True
        else: self.ids.srs_buttons.opacity=0; self.ids.srs_buttons.disabled=True