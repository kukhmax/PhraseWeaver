import asyncio
from threading import Thread

from kivy.clock import mainthread, Clock
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.screen import MDScreen
from kivymd.uix.spinner import MDSpinner
# ИМПОРТИРУЕМ SNACKBAR, ОН НАМ ЗДЕСЬ НУЖЕН
from kivymd.uix.snackbar import Snackbar

from core.enrichment import enrich_phrase
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CreationScreen(MDScreen):
    deck_id = None
    lang_code = None
    initial_text = None
    enriched_data = None
    spinner = None
    
    def on_enter(self, *args):
        Clock.schedule_once(self.setup_screen, 0)
    
    def setup_screen(self, dt=None):
        if self.spinner:
            self.show_spinner(False)

        self.ids.full_sentence_field.text = ""
        self.ids.keyword_field.text = ""
        self.ids.results_box.clear_widgets()
        self.ids.save_button.disabled = True
        self.enriched_data = None

        if self.initial_text:
            self.ids.full_sentence_field.text = self.initial_text
            self.initial_text = None

    def paste_from_clipboard(self, *args):
        pasted_text = Clipboard.get()
        if pasted_text:
            self.ids.full_sentence_field.text = pasted_text

    def enrich_button_pressed(self):
        keyword = self.ids.keyword_field.text.strip()
        if not keyword:
            return

        self.show_spinner(True)
        thread = Thread(target=self.run_enrichment, args=(keyword,))
        thread.start()

    def run_enrichment(self, keyword):
        if not self.lang_code:
            logging.error("Ошибка: не указан язык колоды!")
            return
        try:
            self.enriched_data = asyncio.run(enrich_phrase(keyword, self.lang_code))
        except Exception as e:
            logging.error(f"Ошибка в потоке обогащения: {e}")
            self.enriched_data = None
        
        self.update_ui_with_results()

    @mainthread
    def update_ui_with_results(self):
        self.show_spinner(False)
        self.ids.results_box.clear_widgets()

        if not self.enriched_data:
            return

        translation_text = f"Перевод: {self.enriched_data.get('translation', 'Не найден')}"
        results_label = MDRaisedButton(text=translation_text)
        self.ids.results_box.add_widget(results_label)
        
        for example in self.enriched_data.get('examples', []):
            example_label = MDRaisedButton(text=example)
            self.ids.results_box.add_widget(example_label)
            
        self.ids.save_button.disabled = False

    @mainthread
    def show_spinner(self, show):
        button = self.ids.get('enrich_button')
        if not button: return
        container = button.parent

        if show:
            button.opacity = 0
            button.disabled = True
            if not self.spinner:
                self.spinner = MDSpinner(size_hint=(None, None), size=(dp(46), dp(46)), pos_hint={'center_x': 0.5})
            container.add_widget(self.spinner, index=container.children.index(button) + 1)
        else:
            button.opacity = 1
            button.disabled = False
            if self.spinner and self.spinner.parent:
                self.spinner.parent.remove_widget(self.spinner)
    
    def save_concept(self):
        if not self.enriched_data or not self.deck_id:
            return

        db_manager = self.db_manager
        
        full_sentence = self.ids.full_sentence_field.text.strip()
        self.enriched_data['full_sentence'] = full_sentence
        
        logging.info("Сохранение концепта в БД...")
        result = db_manager.create_concept_and_cards(
            deck_id=self.deck_id,
            full_sentence=full_sentence,
            enriched_data=self.enriched_data
        )

        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ: Используем "пуленепробиваемый" метод ---
        snackbar_text = ""
        if result == "duplicate":
            logging.warning("Попытка сохранить дубликат.")
            snackbar_text = "Эта фраза уже есть в колоде!"
        elif result:
            logging.info(f"Концепт успешно сохранен с ID {result}.")
            snackbar_text = "Карточка успешно сохранена!"
        else:
            logging.error("Не удалось сохранить концепт.")
            snackbar_text = "Ошибка! Не удалось сохранить карточку."

        # Создаем пустой Snackbar и задаем ему свойства пошагово
        snackbar = Snackbar()
        snackbar.text = snackbar_text
        snackbar.open()

        self.manager.current = 'deck_list'