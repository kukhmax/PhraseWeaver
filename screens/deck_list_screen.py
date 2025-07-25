from functools import partial
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import MDListItem, MDListItemLeadingIcon, MDListItemHeadlineText, MDListItemSupportingText
from kivymd.uix.menu import MDDropdownMenu # ТОЛЬКО ЭТОТ ИМПОРТ ИЗ MENU
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogHeadlineText,
    MDDialogSupportingText, # Нам он не понадобится, но для информации
    MDDialogButtonContainer,
    MDDialogContentContainer,
)

from core.config import SUPPORTED_LANGUAGES

class CreateDeckDialogContent(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = "12dp"
        self.size_hint_y = None
        self.height = "120dp"
        self.deck_name_field = MDTextField(hint_text="Название колоды", mode="filled")
        self.add_widget(self.deck_name_field)
        self.language_button = MDButton(MDButtonText(text="Выберите язык"), style="outlined")
        self.add_widget(self.language_button)
        self.selected_lang_code = None


class DeckListScreen(MDScreen):
    """Экран для отображения списка колод."""
    dialog = None

    def on_enter(self, *args):
        """
        Метод вызывается, когда экран становится видимым.
        Мы используем Clock.schedule_once, чтобы гарантировать,
        что все 'ids' будут доступны к моменту вызова load_decks.
        """
        Clock.schedule_once(self.load_decks, 0)


    def load_decks(self, dt=None):
        """
        Загружает колоды из БД и отображает их в виде списка.
        """
        # Получаем доступ к нашему менеджеру БД через инстанс приложения
        app = MDApp.get_running_app()
        if not app or not hasattr(app, 'db_manager'):
            return
        decks = app.db_manager.get_all_decks()

        # Находим виджет списка по его id (мы зададим его в KV строке)
        deck_list_widget = self.ids.deck_list
        deck_list_widget.clear_widgets() # Очищаем старый список перед обновлением

        if not decks:
            item = MDListItem()
            item.add_widget(MDListItemLeadingIcon(icon="plus-box-outline"))
            item.add_widget(MDListItemHeadlineText(text="Колод пока нет. Создайте первую!"))
            deck_list_widget.add_widget(item)
            return

        for deck in decks:
            # Считаем карточки для этой колоды
            review_count = app.db_manager.count_cards_for_review(deck['id'])
            lang_name = SUPPORTED_LANGUAGES.get(deck['lang_code'], deck['lang_code'].upper())

            item = MDListItem(
                on_release=lambda x, deck_id=deck['id']: self.go_to_training(deck_id)
            )
            item.add_widget(
                MDListItemLeadingIcon(icon="cards-outline")
            )
            item.add_widget(
                MDListItemHeadlineText(text=f"{deck['name']}")
            )
            item.add_widget(
                MDListItemSupportingText(text=f"Язык: {lang_name} | К повторению: {review_count}")
            )
            deck_list_widget.add_widget(item)

    # def on_deck_press(self, deck_id):
    #     """ Обработчик нажатия на колоду."""
    #     print(f"Нажата колода с ID: {deck_id}. Переход пока не реализован.")

    def go_to_training(self, deck_id):
        """Переходит на экран тренировки для выбранной колоды."""
        app = MDApp.get_running_app()
        # Проверяем, есть ли что повторять
        if app.db_manager.count_cards_for_review(deck_id) == 0:
            print("В этой колоде нет карточек для повторения.")
            # Можно показать Snackbar
            return
            
        training_screen = app.sm.get_screen('training_screen')
        training_screen.deck_id = deck_id # Передаем ID колоды на экран тренировки
        app.sm.current = 'training_screen'

    def show_create_deck_dialog(self):
        """Показывает диалог для создания новой колоды (API KivyMD 2.0)."""
        if self.dialog:
            return

        dialog_content = CreateDeckDialogContent()
        
        menu_items = [{
            "text": lang_name,
            "on_release": lambda x=lang_code, button=dialog_content.language_button: self.set_language(x, button),
        } for lang_code, lang_name in SUPPORTED_LANGUAGES.items()]
        self.menu = MDDropdownMenu(caller=dialog_content.language_button, items=menu_items, width_mult=4)
        dialog_content.language_button.on_release = self.menu.open

        # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Собираем диалог по-новому ---
        self.dialog = MDDialog(
            # 1. Добавляем заголовок
            MDDialogHeadlineText(text="Создать новую колоду"),
            # 2. Добавляем наш кастомный контент
            MDDialogContentContainer(dialog_content),
            # 3. Добавляем контейнер для кнопок
            MDDialogButtonContainer(
                # И в него сами кнопки
                MDButton(
                    MDButtonText(text="ОТМЕНА"),
                    style="text", # Текстовый стиль для кнопок отмены
                    on_release=self.close_dialog
                ),
                MDButton(
                    MDButtonText(text="СОЗДАТЬ"),
                    style="text",
                    on_release=lambda x, content=dialog_content: self.create_deck_action(content)
                ),
                spacing="8dp",
            ),
        )
        self.dialog.open()

    def set_language(self, lang_code, button):
        """Обработчик выбора языка в меню."""
        # Сохраняем выбранный код в самом объекте контента диалога
        button.parent.selected_lang_code = lang_code
        
        # Обновляем текст на кнопке
        for child in button.children:
            if isinstance(child, MDButtonText):
                child.text = SUPPORTED_LANGUAGES.get(lang_code)
                break
        self.menu.dismiss()
        
    def close_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    def create_deck_action(self, content):
        """Действие по кнопке 'СОЗДАТЬ'."""
        deck_name = content.deck_name_field.text.strip()
        lang_code = content.selected_lang_code
        
        if not deck_name or not lang_code:
            content.deck_name_field.error_text = "Введите название" if not deck_name else ""
            return

        app = MDApp.get_running_app()
        app.db_manager.create_deck(deck_name, lang_code)
        self.close_dialog()
        Clock.schedule_once(self.load_decks) # Обновляем список с небольшой задержкой

    def show_add_to_deck_menu(self, clipboard_text: str | None = None):
        app = MDApp.get_running_app()
        all_decks = app.db_manager.get_all_decks()
        
        if not all_decks:
            self.show_create_deck_dialog()
            return

        # Создаем меню из существующих колод
        menu_items = []
        for deck in all_decks:
            # Создаем частичную функцию, "замораживая" deck и clipboard_text
            # Мы передаем сам метод go_to_creation_screen и его будущие аргументы
            callback = partial(self.go_to_creation_screen, deck, clipboard_text)
            
            menu_items.append({
                "text": deck['name'],
                "on_release": callback, # Передаем готовый callback
            })

        self.menu = MDDropdownMenu(
            caller=self.ids.add_card_button, 
            items=menu_items, 
            width_mult=4
        )
        self.menu.open()

    def go_to_creation_screen(self, deck_info: dict, initial_text: str | None = None):
        """Переходит на экран создания карточки, передавая данные о колоде."""
        if hasattr(self, 'menu') and self.menu:
            self.menu.dismiss()
            
        app = MDApp.get_running_app()
        
        creation_screen = app.sm.get_screen('creation_screen')
        creation_screen.deck_id = deck_info['id']
        creation_screen.lang_code = deck_info['lang_code']
        # Устанавливаем текст, который будет вставлен на экране создания
        creation_screen.initial_text = initial_text
        
        app.sm.current = 'creation_screen'
