import asyncio
from threading import Thread

from kivy.clock import mainthread
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText # ИЗМЕНЕННЫЙ ИМПОРТ
from kivymd.uix.screen import MDScreen
from kivymd.uix.progressindicator import MDCircularProgressIndicator

from core.enrichment import enrich_phrase

class CreationScreen(MDScreen):
    deck_id = None # Будем передавать ID колоды при переходе на этот экран
    enriched_data = None # Здесь будем хранить обогащенные данные

    def on_enter(self, *args):
        """Планируем очистку экрана."""
        Clock.schedule_once(self.setup_screen, 0)
    
    # Создаем новый метод, который будет вызываться Clock
    def setup_screen(self, dt=None):
        """Очищаем состояние экрана при входе."""
        self.ids.full_sentence_field.text = ""
        self.ids.keyword_field.text = ""
        self.ids.results_box.clear_widgets()
        self.ids.save_button.disabled = True
        self.enriched_data = None
        
        app = MDApp.get_running_app()
        current_screen = getattr(app.sm, 'current_screen', None)
        if current_screen:
            self.deck_id = getattr(current_screen, 'deck_id', None)

    def enrich_button_pressed(self):
        """Запускает процесс обогащения в отдельном потоке."""
        keyword = self.ids.keyword_field.text.strip()
        if not keyword:
            # Можно добавить всплывающее уведомление
            print("Ключевая фраза не может быть пустой!")
            return

        # Показываем спиннер и блокируем кнопку
        self.show_spinner(True)
        
        # Запускаем тяжелую сетевую операцию в отдельном потоке,
        # чтобы не блокировать UI
        thread = Thread(target=self.run_enrichment, args=(keyword,))
        thread.start()

    def run_enrichment(self, keyword):
        """Выполняет асинхронную функцию обогащения."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.enriched_data = loop.run_until_complete(enrich_phrase(keyword))
        loop.close()
        # Когда данные получены, вызываем метод для обновления UI в главном потоке
        self.update_ui_with_results()

    @mainthread
    def update_ui_with_results(self):
        """Обновляет UI с полученными данными (безопасно для потоков)."""
        self.show_spinner(False)
        self.ids.results_box.clear_widgets()

        if not self.enriched_data:
            # Обработка случая, если ничего не нашлось
            return

        # ИЗМЕНЕНО: Создаем кнопки по-новому
        translation_text = f"Перевод: {self.enriched_data.get('translation', 'Не найден')}"
        results_label = MDButton(
            MDButtonText(text=translation_text),
            style="tonal",
        )
        self.ids.results_box.add_widget(results_label)
        
        for example in self.enriched_data.get('examples', []):
            example_label = MDButton(
                MDButtonText(text=example),
                style="outlined"
            )
            self.ids.results_box.add_widget(example_label)
            
        self.ids.save_button.disabled = False

    @mainthread
    def show_spinner(self, show):
        """Показывает или прячет спиннер загрузки."""
        spinner_id = "spinner"
        container = self.ids.get('enrich_button_container')
        if not container:
            return

        if show:
            # Прячем кнопку, чтобы спиннер встал на ее место
            self.ids.enrich_button.opacity = 0
            self.ids.enrich_button.disabled = True
            
            if not self.ids.get(spinner_id):
                # ИСПОЛЬЗУЕМ НОВЫЙ КЛАСС
                spinner = MDCircularProgressIndicator(type="indeterminate") # 'indeterminate' значит "крутится без конца"
                spinner.id = spinner_id
                # Добавляем его в контейнер
                container.add_widget(spinner)
        else:
            # Показываем кнопку обратно
            self.ids.enrich_button.opacity = 1
            self.ids.enrich_button.disabled = False
            spinner = self.ids.get(spinner_id)
            if spinner:
                container.remove_widget(spinner)
    
    def save_concept(self):
        """Сохраняет новый концепт и карточки в базу данных."""
        if not self.enriched_data or not self.deck_id:
            return
            
        print("Сохранение в БД...")
        app = MDApp.get_running_app()
        app.sm.current = 'deck_list'