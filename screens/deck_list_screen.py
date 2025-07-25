from functools import partial
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
# ИСПРАВЛЕНО: Импортируем конкретные кнопки
from kivymd.uix.button import MDFlatButton, MDRaisedButton
# ИСПРАВЛЕНО: Классический MDDialog
from kivymd.uix.dialog import MDDialog
# ИСПРАВЛЕНО: Классические элементы списка
from kivymd.uix.list import OneLineAvatarIconListItem, IRightBodyTouch
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField

from core.config import SUPPORTED_LANGUAGES


# ИСПРАВЛЕНО: Вспомогательный класс для иконки, чтобы она была кликабельной
class ListItemWithRightIcon(OneLineAvatarIconListItem):
    pass

class RightIconWidget(IRightBodyTouch, MDFlatButton):
    pass


class CreateDeckDialogContent(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = "12dp"
        self.size_hint_y = None
        self.height = "120dp"

        self.deck_name_field = MDTextField(hint_text="Название колоды", mode="fill")
        self.language_button = MDRaisedButton(text="Выберите язык")
        self.add_widget(self.deck_name_field)
        self.add_widget(self.language_button)
        self.selected_lang_code = None


class DeckListScreen(MDScreen):
    dialog = None

    def on_enter(self, *args):
        Clock.schedule_once(self.load_decks, 0)

    def load_decks(self, dt=None):
        if not hasattr(self, 'db_manager'): return
        decks = self.db_manager.get_all_decks()

        deck_list_widget = self.ids.deck_list_container
        deck_list_widget.clear_widgets()

        if not decks:
            item = OneLineAvatarIconListItem(text="Колод пока нет. Создайте первую!")
            deck_list_widget.add_widget(item)
            return

        for deck in decks:
            review_count = self.db_manager.count_cards_for_review(deck['id'])
            lang_name = SUPPORTED_LANGUAGES.get(deck['lang_code'], deck['lang_code'].upper())

            item = OneLineAvatarIconListItem(
                text=f"{deck['name']} ({lang_name})",
                secondary_text=f"К повторению: {review_count}",
                on_release=lambda x, current_deck=deck: self.go_to_creation_screen(current_deck)
            )
            # ИСПРАВЛЕНО: Добавляем правую иконку для тренировки
            right_icon = RightIconWidget(
                text="ТРЕНИРОВАТЬ",
                on_press=lambda x, deck_id=deck['id']: self.go_to_training(deck_id)
            )
            item.add_widget(right_icon)
            deck_list_widget.add_widget(item)

    def go_to_training(self, deck_id):
        if self.db_manager.count_cards_for_review(deck_id) == 0:
            return
            
        training_screen = self.manager.get_screen('training_screen')
        training_screen.deck_id = deck_id
        self.manager.current = 'training_screen'

    def show_create_deck_dialog(self):
        if self.dialog: return

        content = CreateDeckDialogContent()
        
        menu_items = [{
            "text": lang_name,
            "viewclass": "OneLineListItem",
            "on_release": lambda x=lang_code, y=content: self.set_language(x, y),
        } for lang_code, lang_name in SUPPORTED_LANGUAGES.items()]
        
        self.menu = MDDropdownMenu(caller=content.language_button, items=menu_items, width_mult=4)
        content.language_button.on_release = self.menu.open

        # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
        self.dialog = MDDialog(
            title="Создать новую колоду",
            type="custom",
            content_cls=content,
            # Добавляем это свойство, чтобы окно не закрывалось само по себе
            auto_dismiss=False, 
            buttons=[
                MDFlatButton(text="ОТМЕНА", on_release=self.close_dialog),
                MDRaisedButton(text="СОЗДАТЬ", on_release=lambda x: self.create_deck_action(content)),
            ],
        )
        self.dialog.open()

    def set_language(self, lang_code, content_cls):
        content_cls.selected_lang_code = lang_code
        content_cls.language_button.text = SUPPORTED_LANGUAGES.get(lang_code)
        self.menu.dismiss()
        
    def close_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    def create_deck_action(self, content):
        deck_name = content.deck_name_field.text.strip()
        lang_code = content.selected_lang_code
        
        if not deck_name or not lang_code: return

        self.db_manager.create_deck(deck_name, lang_code)
        self.close_dialog()
        self.load_decks()

    def show_add_to_deck_menu(self, clipboard_text=None):
        all_decks = self.db_manager.get_all_decks()
        if not all_decks:
            self.show_create_deck_dialog()
            return

        menu_items = []
        for deck in all_decks:
            callback = partial(self.go_to_creation_screen, deck, clipboard_text)
            menu_items.append({
                "text": deck['name'],
                "viewclass": "OneLineListItem",
                "on_release": callback,
            })

        self.menu = MDDropdownMenu(
            caller=self.ids.add_card_button, 
            items=menu_items, 
            width_mult=4
        )
        self.menu.open()

    def go_to_creation_screen(self, deck_info, initial_text=None):
        if hasattr(self, 'menu') and self.menu: self.menu.dismiss()
            
        creation_screen = self.manager.get_screen('creation_screen')
        creation_screen.deck_id = deck_info['id']
        creation_screen.lang_code = deck_info['lang_code']
        creation_screen.initial_text = initial_text
        
        self.manager.current = 'creation_screen'