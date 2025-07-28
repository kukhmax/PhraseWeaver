# Файл: screens/settings_screen.py (ФИНАЛЬНАЯ ВЕРСИЯ)
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget
from core.config import SUPPORTED_LANGUAGES
from core.localization import TRANSLATIONS, translator

class SettingsScreen(MDScreen):
    dialog = None
    app = None

    def on_enter(self, *args):
        if not self.app: self.app = MDApp.get_running_app()
        self.on_language_change()

    def on_language_change(self):
        """Обновляет весь текст на экране в соответствии с выбранным языком."""
        # Убедимся, что все id на месте перед обновлением
        if self.ids:
            self.ids.top_bar.title = self.app.translator.t('settings_title')
            self.ids.lang_settings_label.text = self.app.translator.t('language_settings')
            self.ids.target_lang_item.text = self.app.translator.t('translate_to')
            self.ids.ui_lang_item.text = self.app.translator.t('interface_language')
        self.load_current_settings()

    def load_current_settings(self):
        target_lang = self.app.db_manager.get_setting('target_language', 'ru')
        self.ids.target_lang_item.secondary_text = SUPPORTED_LANGUAGES.get(target_lang, 'Unknown')
        
        ui_lang = self.app.db_manager.get_setting('ui_language', 'ru')
        self.ids.ui_lang_item.secondary_text = TRANSLATIONS.get(ui_lang, {}).get('language_name', ui_lang)

    def show_target_language_dialog(self):
        if self.dialog: return
        
        items = []
        for code, name in SUPPORTED_LANGUAGES.items():
            item = OneLineAvatarIconListItem(text=name, on_release=lambda x, c=code: self.set_target_language(c))
            item.add_widget(IconLeftWidget(icon="translate"))
            items.append(item)
            
        self.dialog = MDDialog(title=self.app.translator.t('select_target_language'), type="simple", items=items)
        self.dialog.bind(on_dismiss=self.close_dialog) # <-- САМОЕ ГЛАВНОЕ ИСПРАВЛЕНИЕ
        self.dialog.open()

    def set_target_language(self, lang_code):
        self.app.db_manager.set_setting('target_language', lang_code)
        self.load_current_settings()
        self.close_dialog()

    def show_ui_language_dialog(self):
        if self.dialog: return

        available_ui_langs = {code: data['language_name'] for code, data in TRANSLATIONS.items()}
        items = []
        for code, name in available_ui_langs.items():
            item = OneLineAvatarIconListItem(text=name, on_release=lambda x, c=code: self.set_ui_language(c))
            item.add_widget(IconLeftWidget(icon="cog-outline"))
            items.append(item)
            
        self.dialog = MDDialog(title=self.app.translator.t('select_ui_language'), type="simple", items=items)
        self.dialog.bind(on_dismiss=self.close_dialog) # <-- САМОЕ ГЛАВНОЕ ИСПРАВЛЕНИЕ
        self.dialog.open()

    def set_ui_language(self, lang_code):
        self.app.db_manager.set_setting('ui_language', lang_code)
        self.app.translator.set_language(lang_code)
        self.app.reload_ui()
        self.close_dialog()

    def close_dialog(self, *args):
        """Этот метод теперь вызывается ВСЕГДА, когда диалог закрывается."""
        if self.dialog:
            self.dialog = None # <-- Очищаем состояние