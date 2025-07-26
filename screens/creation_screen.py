# Файл: screens/creation_screen.py

import asyncio
from threading import Thread

from kivy.clock import mainthread
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.snackbar import Snackbar

from core.enrichment import enrich_phrase
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CreationScreen(MDScreen):
    spinner = None
    
    def on_pre_enter(self, *args):
        self.show_spinner(False)

    def paste_from_clipboard(self, *args):
        # Этот метод не был в прошлом файле, возвращаем его
        from kivy.core.clipboard import Clipboard
        pasted_text = Clipboard.get()
        if pasted_text:
            self.ids.full_sentence_field.text = pasted_text

    def enrich_button_pressed(self):
        keyword = self.ids.keyword_field.text.strip()
        full_sentence = self.ids.full_sentence_field.text.strip()
        
        if not keyword:
            Snackbar(text="Ключевая фраза не может быть пустой!").open()
            return

        self.show_spinner(True)
        thread = Thread(target=self.run_enrichment, args=(
            self.manager.current_deck_id,
            self.manager.current_lang_code,
            keyword, 
            full_sentence
        ))
        thread.start()

    def run_enrichment(self, deck_id, lang_code, keyword, full_sentence):
        """Выполняет обогащение и вызывает метод для перехода на другой экран."""
        print("\n--- DEBUG: НАЧАЛО ФОНОВОГО ПОТОКА ---\n")
        enriched_data = asyncio.run(enrich_phrase(keyword, lang_code))
        print(f"\n--- DEBUG: ФОНОВЫЙ ПОТОК ЗАВЕРШЕН. РЕЗУЛЬТАТ: {'ЕСТЬ ДАННЫЕ' if enriched_data else 'НЕТ ДАННЫХ'} ---\n")
        
        # Передаем все нужные данные на следующий экран
        self.go_to_curation_screen(deck_id, full_sentence, enriched_data)

    @mainthread
    def go_to_curation_screen(self, deck_id, full_sentence, enriched_data):
        self.show_spinner(False)
        
        if not enriched_data or not enriched_data.get('examples'):
            # --- ИСПРАВЛЕНО ОКОНЧАТЕЛЬНО ---
            # Применяем наш "пуленепробиваемый" метод
            error_text = f"Примеры для '{enriched_data.get('keyword', '')}' не найдены."
            snackbar = Snackbar()
            snackbar.text = error_text
            snackbar.open()
            return
            
        curation_screen = self.manager.get_screen('curation_screen')
        
        curation_screen.deck_id = deck_id
        curation_screen.full_sentence = full_sentence
        curation_screen.enriched_data = enriched_data
        
        self.manager.current = 'curation_screen'

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
            container.add_widget(self.spinner, index=container.children.index(button))
        else:
            button.opacity = 1
            button.disabled = False
            if self.spinner and self.spinner.parent:
                self.spinner.parent.remove_widget(self.spinner)