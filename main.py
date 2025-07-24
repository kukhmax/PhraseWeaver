import os
from kivymd.app import MDApp
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager

from core.database import DatabaseManager
from screens.deck_list_screen import DeckListScreen
from screens.creation_screen import CreationScreen
from screens.training_screen import TrainingScreen

# --- Конфигурация для удобства разработки на ПК ---
# Мы устанавливаем фиксированный размер окна, имитирующий экран смартфона.
# Это не повлияет на финальное приложение на Android (там оно будет на весь экран),
# но для разработки на компьютере это очень удобно.
Window.size = (400, 700)

# Загружаем строку с KV разметкой. Это как HTML для веба.
# Мы описываем здесь структуру виджетов.
KV = """
ScreenManager:
    # id: screen_manager
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
        ScrollView:
            MDList:
                id: deck_list
    MDFabButton: # <--- ИСПРАВЛЕНО
        icon: "plus"
        pos_hint: {"right": 0.95, "bottom": 0.05}
        on_release: root.show_create_deck_dialog()
<CreationScreen>:
    name: 'creation_screen'
    MDBoxLayout:
        orientation: 'vertical'
        spacing: "12dp"
        padding: "12dp"

        MDTopAppBar:
            title: "Создать карточку"
            pos_hint: {"top": 1}
            left_action_items: [["arrow-left", lambda x: app.sm.switch_to(app.sm.get_screen('deck_list'), direction='right')]]

        MDTextField:
            id: full_sentence_field
            hint_text: "Полное предложение (контекст)"
            helper_text: "Пример: It turned out to be a blessing in disguise."
            helper_text_mode: "on_focus"
            mode: "filled"

        MDTextField:
            id: keyword_field
            hint_text: "Ключевая фраза"
            helper_text: "Пример: a blessing in disguise"
            helper_text_mode: "on_focus"
            mode: "filled"

        MDBoxLayout:
            id: enrich_button_container
            adaptive_height: True
            pos_hint: {"center_x": 0.5}
            MDButton:
                id: enrich_button
                style: "filled" # 'filled' это аналог 'raised'
                on_release: root.enrich_button_pressed()
                MDButtonText:
                    text: "Обогатить ✨"
        
        ScrollView:
            MDBoxLayout:
                id: results_box
                orientation: 'vertical'
                adaptive_height: True
                spacing: "8dp"
                padding: "8dp"

        MDButton:
            id: save_button
            style: "filled" # или 'tonal'
            disabled: True
            on_release: root.save_concept()
            pos_hint: {"center_x": 0.5}
            MDButtonText:
                text: "Сохранить в колоду"
<TrainingScreen>:
    name: 'training_screen'
    MDBoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            title: "Тренировка"
            pos_hint: {"top": 1}
            left_action_items: [["arrow-left", lambda x: app.sm.switch_to(app.sm.get_screen('deck_list'), direction='right')]]

        MDLinearProgressIndicator:
            id: progress_bar
            value: 0

        MDBoxLayout:
            orientation: 'vertical'
            padding: "24dp"
            spacing: "24dp"
            
            MDCard:
                style: "filled"
                padding: "16dp"
                MDLabel:
                    id: front_card_label
                    text: "Загрузка карточки..."
                    halign: "center"
                    # ИСПРАВЛЕНО: два свойства вместо одного
                    font_style: "Title" 
                    role: "large"

            MDCard:
                style: "outlined"
                padding: "16dp"
                MDLabel:
                    id: back_card_label
                    text: ""
                    halign: "center"
                    # ИСПРАВЛЕНО: два свойства вместо одного
                    font_style: "Headline"
                    role: "small"
                    
            MDButton:
                style: "filled"
                pos_hint: {"center_x": 0.5}
                on_release: root.show_answer()
                MDButtonText:
                    text: "Показать ответ"
        
        MDBoxLayout:
            id: answer_buttons
            orientation: 'horizontal'
            adaptive_height: True
            padding: "16dp"
            spacing: "16dp"
            pos_hint: {"center_x": 0.5}
            opacity: 0 
            disabled: True

            MDButton:
                style: "tonal"
                on_release: root.evaluate_answer("again")
                MDButtonText:
                    text: "Снова"
            MDButton:
                style: "tonal"
                on_release: root.evaluate_answer("good")
                MDButtonText:
                    text: "Хорошо"
            MDButton:
                style: "tonal"
                on_release: root.evaluate_answer("easy")
                MDButtonText:
                    text: "Легко"
"""


class PhraseWeaverApp(MDApp):
    """
    Главный класс нашего приложения. Он наследуется от MDApp (Material Design App),
    что дает нам доступ ко всем виджетам и стилям KivyMD.
    """

    db_manager = None # Добавляем атрибут для хранения менеджера БД

    def build(self):
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.theme_style = "Light"

        self.db_manager = DatabaseManager()
        self.sm = Builder.load_string(KV)
        
        if not self.db_manager.get_all_decks():
            self.db_manager.create_deck("General")

        return self.sm

    def on_stop(self):
        """
        Этот метод Kivy вызывает, когда приложение закрывается.
        Идеальное место, чтобы закрыть соединение с БД.
        """
        if self.db_manager:
            self.db_manager.close()

def setup_environment():
    """
    Функция для подготовки окружения перед запуском приложения.
    Например, создание необходимых папок.
    """
    # ТЗ требует, чтобы аудиофайлы хранились в `assets/audio`.
    # Этот код проверяет, существует ли эта папка, и создает ее, если нет.
    # Это предотвратит ошибки, если приложение попытается сохранить файл в несуществующую директорию.
    if not os.path.exists('assets/audio'):
        os.makedirs('assets/audio')


# --- Точка входа в приложение ---
if __name__ == '__main__':
    # Эта конструкция в Python означает: "выполнять этот код,
    # только если файл запущен напрямую (а не импортирован как модуль)".
    
    # 1. Готовим окружение (создаем папки)
    setup_environment()

    # 2. Создаем экземпляр и Запускаем его. Эта команда запускает цикл событий Kivy,
    # отрисовывает окно и ждет действий пользователя. Программа будет
    # работать до тех пор, пока пользователь не закроет окно.
    PhraseWeaverApp().run()