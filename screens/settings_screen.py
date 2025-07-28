from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.button import MDFlatButton

# Импортируем наш словарь с языками
from core.config import SUPPORTED_LANGUAGES

class SettingsScreen(MDScreen):
    """
    Экран для управления настройками приложения.
    """
    dialog = None
    
    def on_enter(self, *args):
        """Вызывается при входе на экран. Загружает текущие настройки."""
        self.load_current_settings()
        
    def load_current_settings(self):
        """Загружает настройки из БД и обновляет UI."""
        app = MDApp.get_running_app()
        # Получаем код языка, например 'ru'. По умолчанию 'ru'.
        target_lang_code = app.db_manager.get_setting('target_language', 'ru')
        # Получаем полное имя, например 'Russian'.
        target_lang_name = SUPPORTED_LANGUAGES.get(target_lang_code, 'Unknown')
        
        # Обновляем текст в нашем элементе списка
        self.ids.target_lang_item.secondary_text = target_lang_name
        
    def show_target_language_dialog(self):
        """Открывает диалог выбора языка."""
        if self.dialog:
            return

        # Создаем контейнер для списка языков
        list_content = MDList()
        
        # Динамически создаем по одному элементу на каждый язык
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            item = OneLineListItem(
                text=lang_name,
                # При нажатии вызываем set_target_language с кодом этого языка
                on_release=lambda x, code=lang_code: self.set_target_language(code)
            )
            list_content.add_widget(item)

        # Создаем и показываем сам диалог
        self.dialog = MDDialog(
            title="Выберите язык для перевода",
            type="custom",
            content_cls=list_content,
            buttons=[MDFlatButton(text="ОТМЕНА", on_release=self.close_dialog)]
        )
        self.dialog.open()

    def set_target_language(self, lang_code):
        """Сохраняет выбор пользователя и обновляет экран."""
        app = MDApp.get_running_app()
        app.db_manager.set_setting('target_language', lang_code)
        
        # Обновляем текст на экране, чтобы пользователь видел изменения
        self.load_current_settings()
        
        # Закрываем диалоговое окно
        self.close_dialog()

    def close_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None