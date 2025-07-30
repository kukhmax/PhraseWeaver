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

from core.localization import translator
from core.database import DatabaseManager

from screens.deck_list_screen import DeckListScreen
from screens.creation_screen import CreationScreen
from screens.training_screen import TrainingScreen
from screens.curation_screen import CurationScreen
from screens.stats_screen import StatsScreen
from screens.settings_screen import SettingsScreen

Window.size = (460, 760)


class PhraseWeaverApp(MDApp):

    translator = translator
    sm = None
    db_manager = None

    def on_start(self):
        Clock.schedule_once(self.check_clipboard, 1)
        ui_lang = self.db_manager.get_setting('ui_language', 'ru')
        self.translator.set_language(ui_lang)

    def check_clipboard(self, *args):
        clipboard_text = Clipboard.get().strip()
        if not clipboard_text:
            return

        # 1. Создаем АБСОЛЮТНО ПУСТОЙ Snackbar
        snackbar = Snackbar()

        # 2. Устанавливаем его свойства ПОСЛЕ создания
        snackbar.text = f'Создать карточку из: "{clipboard_text[:30]}..."?'

        # 3. Создаем кнопку
        snackbar_button = MDFlatButton(
            text="СОЗДАТЬ",
            theme_text_color="Custom",
            text_color=self.theme_cls.primary_color,
            on_release=lambda x: self.create_card_from_clipboard())

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
        # 1. Меняем основную палитру на "Зеленый"
        self.theme_cls.primary_palette = "Green"
        # Можно настроить оттенок, например 'A700' для яркости
        self.theme_cls.primary_hue = "600"
        self.theme_cls.accent_palette = "LightGreen"
        self.theme_cls.theme_style = "Light"  

        self.db_manager = DatabaseManager()
        ui_lang = self.db_manager.get_setting('ui_language', 'ru')
        self.translator.set_language(ui_lang)

        self.sm = Builder.load_file('phraseweaver.kv')

        for screen in self.sm.screens:
            screen.app = self
            screen.manager = self.sm  # `manager` теперь тоже устанавливается здесь
            screen.db_manager = self.db_manager

        # 3. Создаем колоду по умолчанию, если нужно.
        if not self.db_manager.get_all_decks():
            self.db_manager.create_deck("General", "en")

        # 4. Возвращаем готовый ScreenManager.
        return self.sm

    def reload_ui(self):
        """ПРОХОДИТ ПО ВСЕМ ЭКРАНАМ И ВЫЗЫВАЕТ ИХ МЕТОД ОБНОВЛЕНИЯ ЯЗЫКА."""
        for screen in self.sm.screens:
            if hasattr(screen, 'on_language_change'):
                screen.on_language_change()


if __name__ == '__main__':
    # Убеждаемся, что папки существуют, прямо перед запуском
    if not os.path.exists('assets'):
        os.makedirs('assets/audio')
        os.makedirs('assets/images')
    if not os.path.exists('assets/audio'): os.makedirs('assets/audio')
    if not os.path.exists('assets/images'): os.makedirs('assets/images')

    PhraseWeaverApp().run()
