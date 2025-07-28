import os
import kivymd
from kivymd.app import MDApp
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager
from kivy.core.clipboard import Clipboard
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.button import MDFlatButton

from core.database import DatabaseManager
from screens.deck_list_screen import DeckListScreen
from screens.creation_screen import CreationScreen
from screens.training_screen import TrainingScreen
from screens.curation_screen import CurationScreen
from screens.stats_screen import StatsScreen
from screens.settings_screen import SettingsScreen


# Window.size = (400, 700)

class PhraseWeaverApp(MDApp):
    sm = None
    db_manager = None

    def on_start(self):
        Clock.schedule_once(self.check_clipboard, 1)
        
    def check_clipboard(self, *args):
        clipboard_text = Clipboard.get().strip()
        if not clipboard_text:
            return
        
        # --- ФИНАЛЬНОЕ ИЗМЕНЕНИЕ: Самый надежный способ ---

        # 1. Создаем АБСОЛЮТНО ПУСТОЙ Snackbar
        snackbar = Snackbar()
        
        # 2. Устанавливаем его свойства ПОСЛЕ создания
        snackbar.text = f'Создать карточку из: "{clipboard_text[:30]}..."?'
        
        # 3. Создаем кнопку
        snackbar_button = MDFlatButton(
            text="СОЗДАТЬ",
            theme_text_color="Custom",
            text_color=self.theme_cls.primary_color,
            on_release=lambda x: self.create_card_from_clipboard()
        )
        
        # 4. Добавляем кнопку к Snackbar
        snackbar.buttons = [snackbar_button]
        
        # 5. Открываем
        snackbar.open()


    def create_card_from_clipboard(self):
        text = Clipboard.get().strip()
        deck_list_screen = self.sm.get_screen('deck_list')
        # ИСПРАВЛЕНО: добавил передачу None, чтобы соответствовать определению метода
        deck_list_screen.show_add_to_deck_menu(clipboard_text=text) 


    def build(self):
        print(f"KIVYMD VERSION: {kivymd.__version__}")
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.theme_style = "Light" 

        self.db_manager = DatabaseManager()
        self.sm = ScreenManager()
        
        screens = [
            DeckListScreen(), CreationScreen(), CurationScreen(),
            TrainingScreen(), StatsScreen(), SettingsScreen()
        ]
        for screen in screens:
            screen.app = self
            # Убедимся, что db_manager тоже передается, если это нужно
            if hasattr(screen, 'db_manager'):
                 screen.db_manager = self.db_manager
            self.sm.add_widget(screen)

        if not self.db_manager.get_all_decks():
            self.db_manager.create_deck("General", "en")

        return self.sm

def setup_environment():
    if not os.path.exists('assets/audio'):
        os.makedirs('assets/audio')


if __name__ == '__main__':
    setup_environment()
    PhraseWeaverApp().run()