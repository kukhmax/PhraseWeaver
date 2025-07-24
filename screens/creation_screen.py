import asyncio
from threading import Thread

from kivy.clock import mainthread
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText # ИЗМЕНЕННЫЙ ИМПОРТ
from kivymd.uix.screen import MDScreen
from kivymd.uix.progressindicator import MDCircularProgressIndicator

from core.enrichment import enrich_phrase

import logging

# Настраиваем логирование, чтобы видеть, что происходит внутри модуля
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CreationScreen(MDScreen):
    deck_id = None # Будем передавать ID колоды при переходе на этот экран
    enriched_data = None # Здесь будем хранить обогащенные данные
    spinner = None

    def on_enter(self, *args):
        """Планируем очистку экрана."""
        Clock.schedule_once(self.setup_screen, 0)
    
    # Создаем новый метод, который будет вызываться Clock
    def setup_screen(self, dt=None):
        """Очищаем состояние экрана при входе."""
        if self.spinner:
            self.show_spinner(False)

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
        # Используем asyncio.run() - это более современный и простой способ
        # запустить асинхронную функцию из синхронного кода.
        # Он сам управляет созданием и закрытием цикла.
        try:
            self.enriched_data = asyncio.run(enrich_phrase(keyword))
        except Exception as e:
            print(f"Ошибка в потоке обогащения: {e}")
            self.enriched_data = None
        
        # Когда `asyncio.run` завершится, все асинхронные операции
        # (включая генерацию аудио) уже будут выполнены.
        # Теперь безопасно обновлять UI.
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
        """Показывает или прячет спиннер загрузки (ИСПРАВЛЕНО)."""
        container = self.ids.get('enrich_button_container')
        if not container: return

        if show:
            # Если спиннер уже существует (на всякий случай), сначала удалим его
            if self.spinner and self.spinner.parent:
                self.spinner.parent.remove_widget(self.spinner)
            
            self.ids.enrich_button.opacity = 0
            self.ids.enrich_button.disabled = True
            
            # Создаем новый спиннер и сохраняем ссылку на него
            self.spinner = MDCircularProgressIndicator()
            container.add_widget(self.spinner)
        else:
            self.ids.enrich_button.opacity = 1
            self.ids.enrich_button.disabled = False
            
            # Если ссылка на спиннер существует и у него есть родитель, удаляем
            if self.spinner and self.spinner.parent:
                self.spinner.parent.remove_widget(self.spinner)
            
            self.spinner = None # Сбрасываем ссылку
    
    # ... (в классе CreationScreen)

    def save_concept(self):
        """Сохраняет новый концепт и карточки в базу данных."""
        if not self.enriched_data or not self.deck_id:
            return

        app = MDApp.get_running_app()
        db_manager = app.db_manager
        
        full_sentence = self.ids.full_sentence_field.text.strip()
        # Добавляем полное предложение в enriched_data для удобства
        self.enriched_data['full_sentence'] = full_sentence
        
        logging.info("Сохранение концепта в БД...")
        result = db_manager.create_concept_and_cards(
            deck_id=self.deck_id,
            full_sentence=full_sentence,
            enriched_data=self.enriched_data
        )

        if result == "duplicate":
            # Здесь можно показать пользователю красивое уведомление (Snackbar)
            logging.warning("Попытка сохранить дубликат.")
            # Например: MDApp.get_running_app().show_toast("Эта фраза уже есть!")
        elif result:
            logging.info(f"Концепт успешно сохранен с ID {result}.")
        else:
            logging.error("Не удалось сохранить концепт.")

        # После сохранения возвращаемся на экран колод
        app.sm.current = 'deck_list'