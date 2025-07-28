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


Window.size = (400, 700)

KV = """
ScreenManager:
    DeckListScreen:
    CreationScreen:
    TrainingScreen:
    CurationScreen:
    StatsScreen:
    SettingsScreen:

<DeckListScreen>:
    name: 'deck_list'
    MDBoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "PhraseWeaver"
            elevation: 4
            pos_hint: {"top": 1}
            left_action_items: [["chart-timeline-variant", lambda x: setattr(root.manager, 'current', 'stats_screen')]]
            right_action_items: [["dots-vertical", lambda x: root.open_main_menu()]]
        ScrollView:
            MDList:
                id: deck_list_container
    MDFloatingActionButton:
        id: add_card_button
        icon: "plus"
        pos_hint: {"right": 0.95, "bottom": 0.05}
        on_release: root.show_add_to_deck_menu()

<SettingsScreen>:
    name: 'settings_screen'
    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.bg_light

        MDTopAppBar:
            title: "Настройки"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'deck_list')]]

        ScrollView:
            MDBoxLayout:
                orientation: 'vertical'
                adaptive_height: True
                padding: "16dp"
                spacing: "24dp"

                MDLabel:
                    text: "Языковые настройки"
                    font_style: "H6"
                    adaptive_height: True

                # --- ИСПРАВЛЕНО ЗДЕСЬ: Используем правильный виджет ---
                TwoLineAvatarIconListItem:
                    text: "Я перевожу на"
                    secondary_text: "Русский"
                    id: target_lang_item
                    on_release: root.show_target_language_dialog()
                    
                    IconLeftWidget: # Добавляем иконку слева для красоты
                        icon: "translate"

                    IconRightWidget:
                        icon: "chevron-down"
<StatsScreen>:
    name: 'stats_screen'
    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.bg_light

        MDTopAppBar:
            title: "Ваш Прогресс"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'deck_list')]]

        ScrollView:
            MDBoxLayout:
                orientation: 'vertical'
                adaptive_height: True
                padding: "16dp"
                spacing: "16dp"

                # --- Карточки для ключевых показателей (KPI) ---
                MDBoxLayout:
                    adaptive_height: True
                    spacing: "16dp"

                    MDCard:
                        orientation: 'vertical'
                        padding: "8dp"
                        size_hint_x: 0.5
                        md_bg_color: app.theme_cls.bg_normal
                        MDLabel:
                            id: learned_cards_label
                            text: "0"
                            halign: 'center'
                            font_style: "H4"
                        MDLabel:
                            text: "Карточек выучено"
                            halign: 'center'
                            theme_text_color: "Secondary"

                    MDCard:
                        orientation: 'vertical'
                        padding: "8dp"
                        size_hint_x: 0.5
                        md_bg_color: app.theme_cls.bg_normal
                        MDLabel:
                            id: streak_label
                            text: "0"
                            halign: 'center'
                            font_style: "H4"
                        MDLabel:
                            text: "Ударная серия"
                            halign: 'center'
                            theme_text_color: "Secondary"

                # --- Карточка для графика ---
                MDCard:
                    orientation: 'vertical'
                    padding: "8dp"
                    size_hint_y: None
                    height: "300dp"
                    md_bg_color: app.theme_cls.bg_normal

                    MDLabel:
                        text: "Активность за последнюю неделю"
                        halign: 'center'
                        adaptive_height: True
                        theme_text_color: "Secondary"
                    
                    # Пустой контейнер, куда мы будем вставлять график из Python
                    MDBoxLayout:
                        id: graph_container

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
                    hint_text: "Ключевая слово"
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
        md_bg_color: app.theme_cls.bg_light # Используем цвет фона темы

        # --- ВОТ ГДЕ МЫ РЕГУЛИРУЕМ "ПОЛОСУ" ---
        MDProgressBar:
            id: progress_bar
            value: 0
            # Говорим: "Не масштабируйся по вертикали"
            size_hint_y: None 
            # Говорим: "Твоя высота - всего 4 пикселя"
            height: dp(4) 
        
        # --- Теперь этот контейнер займет ВСЕ оставшееся место ---
        MDBoxLayout:
            orientation: 'vertical'
            padding: "16dp"
            spacing: "16dp"
            
            MDCard:
                id: question_card
                orientation: 'vertical'
                padding: "8dp"
                md_bg_color: app.theme_cls.bg_normal
                size_hint_y: 0.5 # Занимает 50% высоты этой области
                radius: [12, 12, 12, 12]

                Image:
                    id: card_image
                    source: 'assets/placeholder.png'
            
            MDBoxLayout:
                adaptive_height: True
                padding: "8dp"
                MDLabel:
                    id: question_label
                    text: "Загрузка..."
                    halign: 'center'
                    font_style: "H6"
                MDIconButton:
                    id: play_audio_button
                    icon: "volume-high"
                    on_release: root.play_audio()
            
            MDBoxLayout:
                orientation: 'vertical'
                adaptive_height: True
                spacing: "8dp"
                MDTextField:
                    id: answer_input
                    hint_text: "Ваш ответ..."
                    mode: 'fill'
                    icon_right: ""
                    size_hint_y: None
                    height: 0
                    opacity: 0
                    disabled: True
                MDLabel:
                    id: correct_answer_label
                    halign: 'center'
                    theme_text_color: "Secondary"
                    adaptive_height: True

            Widget: # Распорка
            MDRaisedButton:
                id: action_button
                text: "Показать ответ"
                pos_hint: {"center_x": 0.5}
                on_release: root.handle_main_action()
            MDBoxLayout:
                id: srs_buttons
                orientation: 'horizontal'
                adaptive_height: True
                spacing: "8dp"
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
<CurationScreen>:
    name: 'curation_screen'

    MDBoxLayout:
        orientation: 'vertical'

        MDTopAppBar:
            title: "Выберите лучшее"
            # Эта кнопка будет вести обратно на экран создания, если пользователь передумал
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'creation_screen')]]
        
        MDBoxLayout:
            orientation: 'vertical'
            padding: "16dp"
            spacing: "16dp"

            # --- Область для картинки ---
            MDCard:
                size_hint_y: None
                height: "200dp" # Фиксированная высота для предпросмотра
                # Мы будем менять 'source' из Python-кода
                Image:
                    id: image_preview
                    source: 'assets/images/placeholder.png' # ВАЖНО: нужна картинка-заглушка
                    allow_stretch: True
                    keep_ratio: True
                    fit_mode: "contain"

            MDLabel:
                text: "Найденные примеры:"
                halign: "center"
                font_style: "H6"
            
            # --- Область для списка фраз ---
            ScrollView:
                # Этот ScrollView займет все оставшееся место
                MDList:
                    id: examples_list
            
            # --- Финальная кнопка ---
            MDRaisedButton:
                text: "Добавить выбранное"
                pos_hint: {"center_x": 0.5}
                on_release: root.save_curated_items()
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
            self.db_manager.create_deck("General", "en")

        return self.sm

def setup_environment():
    if not os.path.exists('assets/audio'):
        os.makedirs('assets/audio')


if __name__ == '__main__':
    setup_environment()
    PhraseWeaverApp().run()