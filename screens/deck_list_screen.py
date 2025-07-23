from kivymd.uix.screen import MDScreen
from kivymd.uix.list import MDList, OneLineAvatarIconListItem, IconLeftWidget
from kivymd.app import MDApp

class DeckListScreen(MDScreen):
    """Экран для отображения списка колод."""

    def on_pre_enter(self, *args):
        """
        Метод вызывается прямо перед тем, как экран станет видимым.
        Идеальное место для обновления данных на экране.
        """
        self.load_decks()

    def load_decks(self):
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
            # Можно добавить сообщение, если колод нет
            item = OneLineAvatarIconListItem(text="Колод пока нет. Создайте первую!")
            icon = IconLeftWidget(icon="plus-box-outline")
            item.add_widget(icon)
            deck_list_widget.add_widget(item)
            return

        for deck in decks:
            # Для каждой колоды создаем элемент списка
            item = OneLineAvatarIconListItem(
                text=f"{deck['name']}",
                # Добавляем id колоды к виджету, чтобы потом его использовать
                # Например, при клике, чтобы перейти к карточкам этой колоды
                on_release=lambda x, deck_id=deck['id']: self.on_deck_press(deck_id)
            )
            # Добавляем иконку
            icon = IconLeftWidget(icon="cards-outline")
            item.add_widget(icon)
            deck_list_widget.add_widget(item)

    def on_deck_press(self, deck_id):
        """Обработчик нажатия на колоду."""
        print(f"Нажата колода с ID: {deck_id}")
        # Здесь в будущем будет логика перехода на экран карточек этой колоды