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


Window.size = (400, 700)

KV = """
ScreenManager:
    DeckListScreen:
    CreationScreen:
    TrainingScreen:

<DeckListScreen>:
    name: 'deck_list'
    MDBoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "PhraseWeaver"
            elevation: 4
            pos_hint: {"top": 1}
            right_action_items: [["plus-box-outline", lambda x: root.show_create_deck_dialog()]]
        ScrollView:
            MDList:
                id: deck_list_container
    MDFloatingActionButton:
        id: add_card_button
        icon: "plus"
        pos_hint: {"right": 0.95, "bottom": 0.05}
        on_release: root.show_create_deck_dialog()

<CreationScreen>:
    name: 'creation_screen'
    MDBoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "Создать карточку"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'deck_list')]]
        ScrollView:
            MDBoxLayout:
                orientation: 'vertical'
                adaptive_height: True
                spacing: "12dp"
                padding: "24dp"
                MDBoxLayout:
                    orientation: 'horizontal'
                    adaptive_height: True
                    spacing: "8dp"
                    MDTextField:
                        id: full_sentence_field
                        hint_text: "Полное предложение (контекст)"
                        mode: "fill"
                        size_hint_x: 0.9
                    MDIconButton:
                        icon: "clipboard-arrow-down-outline"
                        on_release: root.paste_from_clipboard()
                        pos_hint: {"center_y": 0.5}
                MDTextField:
                    id: keyword_field
                    hint_text: "Ключевая фраза"
                    mode: "fill"
                MDRaisedButton:
                    id: enrich_button
                    text: "Обогатить ✨"
                    on_release: root.enrich_button_pressed()
                    pos_hint: {"center_x": 0.5}
                MDBoxLayout:
                    id: results_box
                    orientation: 'vertical'
                    adaptive_height: True
                    spacing: "8dp"
                Widget:
                    size_hint_y: None
                    height: dp(24)
                MDRaisedButton:
                    id: save_button
                    text: "Сохранить в колоду"
                    disabled: True
                    on_release: root.save_concept()
                    pos_hint: {"center_x": 0.5}

<TrainingScreen>:
    name: 'training_screen'
    MDBoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "Тренировка"
            pos_hint: {"top": 1}
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'deck_list')]]
        MDProgressBar:
            id: progress_bar
            value: 0
        MDBoxLayout:
            orientation: 'vertical'
            padding: "24dp"
            spacing: "24dp"
            MDCard:
                padding: "16dp"
                MDLabel:
                    id: front_card_label
                    text: "Загрузка карточки..."
                    halign: "center"
                    theme_text_color: "Primary"
                    font_style: "H5"
            MDCard:
                padding: "16dp"
                MDLabel:
                    id: back_card_label
                    text: ""
                    halign: "center"
                    theme_text_color: "Secondary"
                    font_style: "H6"
            MDRaisedButton:
                text: "Показать ответ"
                pos_hint: {"center_x": 0.5}
                on_release: root.show_answer()
        MDBoxLayout:
            id: answer_buttons
            orientation: 'horizontal'
            adaptive_height: True
            padding: "16dp"
            spacing: "16dp"
            pos_hint: {"center_x": 0.5}
            opacity: 0 
            disabled: True
            MDRaisedButton:
                text: "Снова"
                on_release: root.evaluate_answer("again")
            MDRaisedButton:
                text: "Хорошо"
                on_release: root.evaluate_answer("good")
            MDRaisedButton:
                text: "Легко"
                on_release: root.evaluate_answer("easy")
"""


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
        self.sm = Builder.load_string(KV)
        
        for screen_name in self.sm.screen_names:
            screen = self.sm.get_screen(screen_name)
            if not hasattr(screen, 'manager'):
                screen.manager = self.sm
            if not hasattr(screen, 'db_manager'):
                screen.db_manager = self.db_manager
            if not hasattr(screen, 'app'):
                screen.app = self

        if not self.db_manager.get_all_decks():
            self.db_manager.create_deck("General")

        return self.sm

    def on_stop(self):
        if self.db_manager:
            self.db_manager.close()

def setup_environment():
    if not os.path.exists('assets/audio'):
        os.makedirs('assets/audio')


if __name__ == '__main__':
    setup_environment()
    PhraseWeaverApp().run()