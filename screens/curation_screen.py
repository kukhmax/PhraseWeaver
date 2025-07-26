from kivy.clock import mainthread
from kivymd.app import MDApp
from kivymd.uix.list import TwoLineAvatarIconListItem, IconRightWidget
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar


class CurationScreen(MDScreen):
    deck_id = None
    full_sentence = None
    enriched_data = None
    
    def on_pre_enter(self, *args):
        self.populate_screen()
        
    def populate_screen(self):
        self.ids.examples_list.clear_widgets()
        
        if not self.enriched_data: return
            
        image_path = self.enriched_data.get('image_path')
        self.ids.image_preview.source = image_path if image_path else 'assets/images/placeholder.png'
        self.ids.image_preview.reload()

        for example in self.enriched_data.get('examples', []):
            original = example.get('original', '')
            translation = example.get('translation', 'Перевод не найден')
            
            item = TwoLineAvatarIconListItem(
                text=original,
                secondary_text=translation
            )
            item._original_phrase = original
            item._translation = translation
            
            delete_icon = IconRightWidget(
                icon="delete-outline",
                on_release=lambda x, list_item=item: self.delete_example(list_item)
            )
            item.add_widget(delete_icon)
            self.ids.examples_list.add_widget(item)

    def delete_example(self, list_item):
        self.ids.examples_list.remove_widget(list_item)

    def save_curated_items(self):
        app = MDApp.get_running_app()
        db_manager = app.db_manager
        
        shared_image_path = self.ids.image_preview.source
        if shared_image_path == 'assets/images/placeholder.png':
            shared_image_path = None

        items_to_save = self.ids.examples_list.children
        
        if not items_to_save:
            snackbar = Snackbar(text="Нет примеров для сохранения!")
            snackbar.open()
            return

        saved_count = 0
        for item in reversed(items_to_save):
            original_phrase = item._original_phrase
            translation = item._translation
            
            item_data = {
                'keyword': original_phrase,
                'translation': translation,
                'image_path': shared_image_path,
                'audio_path': None
            }
            
            result = db_manager.create_concept_and_cards(
                deck_id=self.deck_id,
                full_sentence=original_phrase,
                enriched_data=item_data
            )
            if result and result != "duplicate":
                saved_count += 1

        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # Применяем наш "пуленепробиваемый" метод
        snackbar = Snackbar()
        snackbar.text = f"Успешно добавлено {saved_count} новых карточек!"
        snackbar.open()
        
        self.manager.current = 'deck_list'