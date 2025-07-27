import json, random
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
# Теперь импорт будет работать правильно
from core.srs import calculate_next_due_date

class TrainingScreen(MDScreen):
    deck_id = None; all_cards = []; current_card = None; _current_mode = None
    _session_total = 0

    def on_enter(self, *args):
        self.load_session_cards()
        self.show_next_card()

    def load_session_cards(self):
        app = MDApp.get_running_app()
        self.deck_id = self.manager.current_deck_id
        self.all_cards = app.db_manager.get_cards_for_review(self.deck_id)
        self._session_total = len(self.all_cards) # Запоминаем общее количество
        random.shuffle(self.all_cards)

    def show_next_card(self):
        self._reset_ui()
        if not self.all_cards:
            self.end_training(); return

        self.current_card = self.all_cards.pop(0)
        card_type, front_data = self.current_card['card_type'], json.loads(self.current_card['front'])
        
        if card_type == 'direct_recognition': self._setup_direct_recognition_card(front_data)
        elif card_type == 'reverse_recall': self._setup_reverse_recall_card(front_data)
        elif card_type == 'context_cloze': self._setup_context_cloze_card(front_data)
        
        if self._session_total > 0:
            progress = (self._session_total - len(self.all_cards)) / self._session_total * 100
            self.ids.progress_bar.value = progress

    def _setup_direct_recognition_card(self, data):
        # ... (аналогично предыдущему, но с reload() для картинки)
        self.ids.card_image.source = data.get('image', 'assets/placeholder.png'); self.ids.card_image.reload()
        self.ids.question_label.text = data.get('text', '')
        self.ids.action_button.text = "Показать ответ"; self._current_mode = 'show_answer'
        
    def _setup_reverse_recall_card(self, data):
        # ...
        self.ids.card_image.source = data.get('image', 'assets/placeholder.png'); self.ids.card_image.reload()
        self.ids.question_label.text = data.get('text', '')
        self._show_input_field(True)
        self.ids.action_button.text = "Проверить"; self._current_mode = 'check_answer'

    def _setup_context_cloze_card(self, data):
        # ...
        self.ids.card_image.source = data.get('image', 'assets/placeholder.png'); self.ids.card_image.reload()
        self.ids.question_label.text = data.get('text', '')
        self._show_input_field(True)
        self.ids.action_button.text = "Проверить"; self._current_mode = 'check_answer'

    def handle_main_action(self):
        if self._current_mode == 'show_answer': self.show_correct_answer()
        elif self._current_mode == 'check_answer': self.check_typed_answer()
    
    def check_typed_answer(self):
        user_answer = self.ids.answer_input.text.strip()
        correct_answer = self.current_card['back']
        
        # --- ИЗМЕНЕНИЕ: Добавляем мгновенную обратную связь ---
        if user_answer.lower() == correct_answer.lower():
            self.ids.answer_input.icon_right = "check-circle"
            self.ids.answer_input.icon_right_color_normal = "green"
        else:
            self.ids.answer_input.icon_right = "close-circle"
            self.ids.answer_input.icon_right_color_normal = "red"
            self.ids.correct_answer_label.text = f"Правильно: {correct_answer}"

        self.ids.answer_input.disabled = True # Блокируем поле после ответа
        self._show_srs_buttons(True)
        
    def show_correct_answer(self):
        self.ids.correct_answer_label.text = self.current_card['back']
        self._show_srs_buttons(True)

    def play_audio(self):
        front_data = json.loads(self.current_card['front'])
        audio_path = front_data.get('audio')
        if audio_path:
            sound = SoundLoader.load(audio_path)
            if sound: sound.play()

    def evaluate_answer(self, quality: str):
        app = MDApp.get_running_app()
        card = self.current_card
        
        # --- ИЗМЕНЕНИЕ: Теперь вызов соответствует нашему новому SRS-алгоритму ---
        srs_result = calculate_next_due_date(
            repetitions=card['repetitions'],
            interval=card['interval'],
            ease_factor=card['ease_factor'],
            quality=quality
        )
        
        app.db_manager.update_card_srs(
            card_id=card['id'],
            new_due_date=srs_result['due_date'],
            new_interval=srs_result['interval'],
            new_ease=srs_result['ease_factor'],
            new_reps=srs_result['repetitions']
        )
        self.show_next_card()
        
    def end_training(self):
        self.ids.question_label.text = "Тренировка завершена!"
        # ...
        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'deck_list'), 2)
        
    def _reset_ui(self):
        # ...
        self.ids.srs_buttons.opacity = 0; self.ids.srs_buttons.disabled = True
        self.ids.action_button.disabled = False
        self.ids.correct_answer_label.text = ""
        self.ids.answer_input.text = ""; self.ids.answer_input.icon_right = ""
        self._show_input_field(False)
    
    def _show_input_field(self, show: bool):
        # ...
        if show:
            self.ids.answer_input.height = "48dp"; self.ids.answer_input.opacity = 1; self.ids.answer_input.disabled = False
        else:
            self.ids.answer_input.height = 0; self.ids.answer_input.opacity = 0; self.ids.answer_input.disabled = True
            
    def _show_srs_buttons(self, show: bool):
        # ...
        if show:
            self.ids.srs_buttons.opacity = 1; self.ids.srs_buttons.disabled = False; self.ids.action_button.disabled = True
        else:
            self.ids.srs_buttons.opacity = 0; self.ids.srs_buttons.disabled = True