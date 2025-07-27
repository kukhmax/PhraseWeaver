# Файл: screens/curation_screen.py (СИНХРОНИЗАЦИЯ)
import asyncio
from threading import Thread
from kivy.clock import mainthread
from kivymd.app import MDApp
from kivymd.uix.list import TwoLineAvatarIconListItem, IconRightWidget
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar
from core.enrichment import generate_audio

class CurationScreen(MDScreen):
    deck_id = None; lang_code = None; enriched_data = None
    
    def on_pre_enter(self, *args): self.populate_screen()
        
    def populate_screen(self):
        self.ids.examples_list.clear_widgets()
        if not self.enriched_data: return
        image_path = self.enriched_data.get('image_path')
        self.ids.image_preview.source = image_path if image_path else 'assets/images/placeholder.png'
        self.ids.image_preview.reload()
        for ex in self.enriched_data.get('examples', []):
            item = TwoLineAvatarIconListItem(text=ex.get('original',''), secondary_text=ex.get('translation',''))
            item._original_phrase = ex.get('original','')
            item._translation = ex.get('translation','')
            item.add_widget(IconRightWidget(icon="delete-outline", on_release=lambda x, i=item: self.delete_example(i)))
            self.ids.examples_list.add_widget(item)

    def delete_example(self, list_item): self.ids.examples_list.remove_widget(list_item)
    
    def save_curated_items(self):
        items = self.ids.examples_list.children
        if not items:
            s = Snackbar(); s.text = "Нет примеров для сохранения!"; s.open()
            return

        s = Snackbar(); s.text = "Сохранение... Это может занять несколько секунд."; s.open()
        
        save_data = [{'original': i._original_phrase, 'translation': i._translation} for i in reversed(items)]
        image_path = self.ids.image_preview.source if self.ids.image_preview.source != 'assets/images/placeholder.png' else None
        self.lang_code = self.manager.current_lang_code
        
        thread = Thread(target=self._blocking_save, args=(save_data, image_path))
        thread.start()

    def _blocking_save(self, phrases_data, image_path):
        count = asyncio.run(self._async_save_items(phrases_data, image_path))
        self.on_saving_complete(count)
        
    async def _async_save_items(self, phrases_data, image_path):
        db_manager = MDApp.get_running_app().db_manager
        tasks = [self.process_and_save_item(p, image_path, db_manager) for p in phrases_data]
        results = await asyncio.gather(*tasks)
        return sum(1 for r in results if r)
        
    async def process_and_save_item(self, phrase_info, image_path, db_manager):
        original, translation = phrase_info['original'], phrase_info['translation']
        audio_path = await generate_audio(original, self.lang_code, "example")
        
        item_data = {'keyword': original, 'translation': translation, 'image_path': image_path, 'audio_path': audio_path}
        
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, db_manager.create_concept_and_cards, self.deck_id, original, item_data)
        return result and result != "duplicate"

    @mainthread
    def on_saving_complete(self, count):
        s = Snackbar(); s.text = f"Успешно добавлено {count} новых карточек!"; s.open()
        self.manager.current = 'deck_list'