from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.list import MDListItem, MDListItemLeadingIcon, MDListItemHeadlineText, MDListItemSupportingText
from kivymd.uix.screen import MDScreen

class DeckListScreen(MDScreen):
    """Экран для отображения списка колод."""

    def on_enter(self, *args):
        """
        Метод вызывается, когда экран становится видимым.
        Мы используем Clock.schedule_once, чтобы гарантировать,
        что все 'ids' будут доступны к моменту вызова load_decks.
        """
        # Выполнить self.load_decks() через один кадр (примерно 1/60 секунды).
        # Аргумент 0 означает "на следующем доступном кадре".
        Clock.schedule_once(self.load_decks, 0)


    def load_decks(self, dt=None):
        """
        Загружает колоды из БД и отображает их в виде списка.
        """
        # Получаем доступ к нашему менеджеру БД через инстанс приложения
        app = MDApp.get_running_app()
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
                MDListItemSupportingText(text=f"К повторению: {review_count}"
            ))
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
    
    def go_to_creation_screen(self):
        """Переходит на экран создания карточки."""
        # Для простоты MVP, будем добавлять карточку в первую колоду.
        # В будущем здесь будет диалог выбора колоды.
        app = MDApp.get_running_app()
        all_decks = app.db_manager.get_all_decks()
        if not all_decks:
            # Обработка случая, если нет колод
            print("Сначала создайте колоду!")
            return
            
        first_deck_id = all_decks[0]['id']
        
        # Устанавливаем deck_id в экран создания ДО перехода
        creation_screen = app.sm.get_screen('creation_screen')
        creation_screen.deck_id = first_deck_id
        
        app.sm.current = 'creation_screen'