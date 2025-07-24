import json
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from core.srs import calculate_next_due_date

class TrainingScreen(MDScreen):
    deck_id = None
    cards_to_review = []
    current_card_index = 0
    
    def on_enter(self, *args):
        Clock.schedule_once(self.setup_screen)

    def setup_screen(self, dt=None):
        app = MDApp.get_running_app()
        self.deck_id = app.sm.current_screen.deck_id
        self.cards_to_review = app.db_manager.get_cards_for_review(self.deck_id)
        self.current_card_index = 0
        self.show_next_card()

    def show_next_card(self):
        # Сначала прячем кнопки оценки и "оборот" карточки
        self.ids.answer_buttons.opacity = 0
        self.ids.answer_buttons.disabled = True
        self.ids.back_card_label.text = ""

        if self.current_card_index >= len(self.cards_to_review):
            self.end_training()
            return

        card = self.cards_to_review[self.current_card_index]
        self.ids.front_card_label.text = card['front']
        
        # Обновляем прогресс-бар
        progress = (self.current_card_index + 1) / len(self.cards_to_review) * 100
        self.ids.progress_bar.value = progress

    def show_answer(self):
        if self.current_card_index >= len(self.cards_to_review):
            return
        
        card = self.cards_to_review[self.current_card_index]
        self.ids.back_card_label.text = card['back']
        
        # Показываем кнопки оценки
        self.ids.answer_buttons.opacity = 1
        self.ids.answer_buttons.disabled = False
        
    def evaluate_answer(self, quality: str):
        """Обрабатывает ответ пользователя и обновляет карточку."""
        card = self.cards_to_review[self.current_card_index]
        
        new_srs_level, new_due_date = calculate_next_due_date(card['srs_level'], quality)
        
        app = MDApp.get_running_app()
        app.db_manager.update_card_srs(card['id'], new_srs_level, new_due_date)
        
        self.current_card_index += 1
        self.show_next_card()

    def end_training(self):
        self.ids.front_card_label.text = "Тренировка завершена!"
        # Возвращаемся на главный экран
        app = MDApp.get_running_app()
        app.sm.current = 'deck_list'