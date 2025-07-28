import asyncio
from threading import Thread
from kivy.clock import mainthread
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.snackbar import Snackbar
from kivymd.app import MDApp
from core.enrichment import enrich_phrase
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CreationScreen(MDScreen):
    spinner = None
    initial_text = None

    def on_language_change(self):
        # Перезагружаем колоды, т.к. в них есть переводимые строки
        self.load_decks()
    
    def on_pre_enter(self, *args):
        self.show_spinner(False)
        if self.initial_text:
            self.ids.full_sentence_field.text = self.initial_text
            self.initial_text = None

    def paste_from_clipboard(self, *args):
        from kivy.core.clipboard import Clipboard
        self.ids.full_sentence_field.text = Clipboard.get()

    def enrich_button_pressed(self):
        keyword = self.ids.keyword_field.text.strip()
        full_sentence = self.ids.full_sentence_field.text.strip()
        if not keyword:
            s = Snackbar()
            s.text = self.app.translator.t('no_keyword_error')
            s.open()
            return
            
        self.show_spinner(True)
        thread = Thread(target=self.run_enrichment, args=(
            self.manager.current_deck_id, self.manager.current_lang_code,
            keyword, full_sentence
        ))
        thread.start()

    # --- КЛЮЧЕВОЕ АРХИТЕКТУРНОЕ ИСПРАВЛЕНИЕ ---
    def run_enrichment(self, deck_id, lang_code, keyword, full_sentence):
        app = MDApp.get_running_app()
        # Получаем настройку ПЕРЕД запуском обогащения
        target_lang = app.db_manager.get_setting('target_language', 'ru')

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        enriched_data = None
        try:
            # Передаем ее в enrich_phrase
            enriched_data = loop.run_until_complete(
                enrich_phrase(keyword, full_sentence, lang_code, target_lang)
            )
        finally:
            loop.close()
        self.go_to_curation_screen(deck_id, keyword, full_sentence, enriched_data)

    @mainthread
    def go_to_curation_screen(self, deck_id, keyword, full_sentence, enriched_data):
        self.show_spinner(False)
        if not enriched_data or not enriched_data.get("examples"):
            s = Snackbar(); s.text = f"Не удалось найти примеры для '{keyword}'"; s.open()
            return

        user_original = full_sentence if full_sentence else enriched_data.get('keyword', '')
        user_translation = enriched_data.get('full_sentence_translation') or enriched_data.get('translation', '...')
        # AI теперь сам выделяет тегами, нам не нужно это делать
        user_example = {'original': user_original, 'translation': user_translation}
        
        if 'examples' not in enriched_data: enriched_data['examples'] = []

        # Проверяем, чтобы не добавить дубликат, если AI вернул ту же фразу
        # Убираем теги для сравнения
        clean_user_original = user_original.replace('<b>','').replace('</b>','')
        is_duplicate = any(ex['original'].replace('<b>','').replace('</b>','') == clean_user_original for ex in enriched_data['examples'])
        
        if not is_duplicate:
            enriched_data['examples'].insert(0, user_example)
        
        curation_screen = self.manager.get_screen('curation_screen')
        curation_screen.deck_id = deck_id
        curation_screen.keyword = keyword
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
            container.add_widget(self.spinner)
        else:
            button.opacity=1; button.disabled=False
            if self.spinner and self.spinner.parent: self.spinner.parent.remove_widget(self.spinner)