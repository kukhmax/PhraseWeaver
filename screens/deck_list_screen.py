from functools import partial
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import TwoLineAvatarIconListItem, IRightBodyTouch
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.snackbar import Snackbar

from core.config import SUPPORTED_LANGUAGES


# Вспомогательный класс для правой кнопки, теперь это просто кнопка
class RightButtonWidget(IRightBodyTouch, MDRaisedButton):
    pass


class CreateDeckDialogContent(MDBoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        app = MDApp.get_running_app()
        t = app.translator.t

        self.orientation = "vertical"
        self.spacing = "12dp"
        self.size_hint_y = None
        self.height = "120dp"

        self.deck_name_field = MDTextField(hint_text=t('deck_name'),
                                           mode="fill")
        self.language_button = MDRaisedButton(text=t('select_language'))
        self.add_widget(self.deck_name_field)
        self.add_widget(self.language_button)
        self.selected_lang_code = None


class DeckListScreen(MDScreen):
    dialog = None
    menu = None
    app = None

    def on_enter(self, *args):
        if not self.app:
            self.app = MDApp.get_running_app()
        # Проверяем, что db_manager уже инициализирован
        if hasattr(self.app, "db_manager") and self.app.db_manager:
            # Проверяем, что ids уже доступны
            if 'deck_list_container' in self.ids:
                self.on_language_change()
            else:
                Clock.schedule_once(lambda dt: self.on_enter(), 0.1)
        else:
            Clock.schedule_once(lambda dt: self.on_enter(), 0.1)

    def on_language_change(self):
        """Обновляет текст на виджетах этого экрана."""
        if hasattr(self, 'ids') and self.ids.get('top_bar'):
            self.ids.top_bar.title = self.app.translator.t('deck_list_title')
        self.load_decks()

    def load_decks(self, dt=None):
        decks = self.app.db_manager.get_all_decks()
        deck_list_widget = self.ids.deck_list_container
        deck_list_widget.clear_widgets()
        t = self.app.translator.t
        if not decks:
            item = TwoLineAvatarIconListItem(text=t('no_decks'))
            deck_list_widget.add_widget(item)
            return
        for deck in decks:
            review_count = self.app.db_manager.count_cards_for_review(
                deck['id'])
            total_count = self.app.db_manager.count_all_cards_in_deck(
                deck['id'])
            lang_name = t(deck['lang_code'])
            item = TwoLineAvatarIconListItem(
                text=f"{deck['name']} ({lang_name})",
                secondary_text=
                f"{t('total_cards')}: {total_count} | {t('due_cards')}: {review_count}",
                on_release=lambda x, d=deck: self.go_to_creation_screen(d))
            right_button = RightButtonWidget(
                text="ТРЕН.",
                theme_text_color="Custom",
                text_color=self.app.theme_cls.primary_color,
                on_press=lambda x, d_id=deck['id']: self.go_to_training(d_id))
            item.add_widget(right_button)
            deck_list_widget.add_widget(item)

    def go_to_training(self, deck_id):
        t = self.app.translator.t
        if self.app.db_manager.count_cards_for_review(deck_id) == 0:
            s = Snackbar(text=t('no_cards_for_review'))
            s.open()
            return
        self.manager.current_deck_id = deck_id
        self.manager.current = 'training_screen'

    def open_main_menu(self):
        t = self.app.translator.t
        menu_items = [
            {
                "text": t('create_deck'),
                "leading_icon": "plus-box-outline",
                "on_release": self.show_create_deck_dialog
            },
            {
                "text":
                t('settings'),
                "leading_icon":
                "cog-outline",
                "on_release":
                lambda: setattr(self.manager, 'current', 'settings_screen')
            },
        ]
        if hasattr(self, 'ids') and self.ids.get('top_bar'):
            self.menu = MDDropdownMenu(
                caller=self.ids.top_bar.ids.right_actions.children[0],
                items=menu_items,
                width_mult=4)
            self.menu.open()

    def show_create_deck_dialog(self):
        if self.dialog:
            return
        t = self.app.translator.t
        content = CreateDeckDialogContent()

        menu_items = [{
            "text":
            t(lang_code),
            "viewclass":
            "OneLineListItem",
            "on_release":
            partial(self.set_language, lang_code, content),
        } for lang_code in SUPPORTED_LANGUAGES.keys()]

        self.menu = MDDropdownMenu(caller=content.language_button,
                                   items=menu_items,
                                   width_mult=4)
        content.language_button.on_release = self.menu.open

        self.dialog = MDDialog(
            title=t('create_new_deck'),
            type="custom",
            content_cls=content,
            auto_dismiss=False,
            buttons=[
                MDFlatButton(text=t('cancel'), on_release=self.close_dialog),
                MDRaisedButton(
                    text=t('create'),
                    on_release=lambda x: self.create_deck_action(content))
            ])
        self.dialog.open()

    def set_language(self, lang_code, content_cls, *args):
        content_cls.selected_lang_code = lang_code
        content_cls.language_button.text = self.app.translator.t(lang_code)
        self.menu.dismiss()

    def close_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    def create_deck_action(self, content):
        deck_name, lang_code = content.deck_name_field.text.strip(
        ), content.selected_lang_code
        if not deck_name or not lang_code: return
        self.app.db_manager.create_deck(deck_name, lang_code)
        self.close_dialog()
        self.load_decks()

    def show_add_to_deck_menu(self, clipboard_text=None):
        if self.menu: self.menu.dismiss()
        all_decks = self.app.db_manager.get_all_decks()
        if not all_decks:
            self.show_create_deck_dialog()
            return
        menu_items = [{
            "text":
            deck['name'],
            "viewclass":
            "OneLineListItem",
            "on_release":
            partial(self.go_to_creation_screen, deck, clipboard_text)
        } for deck in all_decks]
        self.menu = MDDropdownMenu(caller=self.ids.add_card_button,
                                   items=menu_items,
                                   width_mult=4)
        self.menu.open()
        self.menu = MDDropdownMenu(caller=self.ids.add_card_button,
                                   items=menu_items,
                                   width_mult=4)
        self.menu.open()

    def go_to_creation_screen(self, deck_info, initial_text=None):
        if self.menu:
            self.menu.dismiss()
        creation_screen = self.manager.get_screen('creation_screen')
        self.manager.current_deck_id = deck_info['id']
        self.manager.current_lang_code = deck_info['lang_code']
        creation_screen.initial_text = initial_text
        self.manager.current = 'creation_screen'
