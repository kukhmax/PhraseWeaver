# Файл: screens/creation_screen.py (ФИНАЛЬНАЯ АРХИТЕКТУРНАЯ ПРАВКА)

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
        from kivy.core.clipboard import Clipboard
        pasted_text = Clipboard.get()
        if pasted_text:
            self.ids.full_sentence_field.text = pasted_text

    def enrich_button_pressed(self):
        keyword = self.ids.keyword_field.text.strip()
        full_sentence = self.ids.full_sentence_field.text.strip()
        if not keyword:
            s = Snackbar(); s.text = "Ключевая фраза не может быть пустой!"; s.open()
            return
            
        self.show_spinner(True)
        thread = Thread(target=self.run_enrichment, args=(
            self.manager.current_deck_id, self.manager.current_lang_code,
            keyword, full_sentence
        ))
        thread.start()

    # --- КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ ЗДЕСЬ ---
    def run_enrichment(self, deck_id, lang_code, keyword, full_sentence):
        """
        Запускает асинхронный код в фоновом потоке ПРАВИЛЬНЫМ СПОСОБОМ.
        """
        # 1. Создаем НОВЫЙ event loop специально для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        enriched_data = None
        try:
            # 2. Запускаем нашу главную асинхронную задачу в этом новом loop'е
            enriched_data = loop.run_until_complete(
                enrich_phrase(keyword, full_sentence, lang_code)
            )
        finally:
            # 3. Гарантированно закрываем loop после завершения работы
            loop.close()

        # Передаем результат в основной поток для обновления UI
        self.go_to_curation_screen(deck_id, full_sentence, enriched_data)

    @mainthread
    def go_to_curation_screen(self, deck_id, full_sentence, enriched_data):
        self.show_spinner(False)
        if not enriched_data:
            s = Snackbar(); s.text = "Не удалось получить данные от AI."; s.open()
            return

        user_original = full_sentence if full_sentence else enriched_data.get('keyword', '')
        user_translation = enriched_data.get('full_sentence_translation') or enriched_data.get('translation', '...')
        user_example = {'original': user_original, 'translation': user_translation}
        
        if 'examples' not in enriched_data:
            enriched_data['examples'] = []
        if not any(ex['original'] == user_original for ex in enriched_data['examples']):
            enriched_data['examples'].insert(0, user_example)
        
        curation_screen = self.manager.get_screen('curation_screen')
        curation_screen.deck_id = deck_id
        curation_screen.keyword = enriched_data.get('keyword')
        curation_screen.enriched_data = enriched_data
        
        self.manager.current = 'curation_screen'

    @mainthread
    def show_spinner(self, show):
        button = self.ids.get('enrich_button')
        if not button: return
        container = button.parent
        if show:
            button.opacity=0; button.disabled=True
            if not self.spinner: self.spinner = MDSpinner(size_hint=(None, None), size=(dp(46), dp(46)), pos_hint={'center_x': 0.5})
            container.add_widget(self.spinner, index=container.children.index(button))
        else:
            button.opacity=1; button.disabled=False
            if self.spinner and self.spinner.parent: self.spinner.parent.remove_widget(self.spinner)