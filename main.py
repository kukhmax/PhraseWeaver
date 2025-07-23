import os
from kivymd.app import MDApp
from kivy.core.window import Window
from core.database import DatabaseManager

# --- Конфигурация для удобства разработки на ПК ---
# Мы устанавливаем фиксированный размер окна, имитирующий экран смартфона.
# Это не повлияет на финальное приложение на Android (там оно будет на весь экран),
# но для разработки на компьютере это очень удобно.
Window.size = (400, 700)


class PhraseWeaverApp(MDApp):
    """
    Главный класс нашего приложения. Он наследуется от MDApp (Material Design App),
    что дает нам доступ ко всем виджетам и стилям KivyMD.
    """

    db_manager = None # Добавляем атрибут для хранения менеджера БД

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

        # Создаем экземпляр менеджера БД при запуске приложения
        self.db_manager = DatabaseManager()
        
        return None
    
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
    audio_path = 'assets/audio'
    if not os.path.exists(audio_path):
        print(f"Creating directory: {audio_path}")
        os.makedirs(audio_path)


# --- Точка входа в приложение ---
if __name__ == '__main__':
    # Эта конструкция в Python означает: "выполнять этот код,
    # только если файл запущен напрямую (а не импортирован как модуль)".
    
    # 1. Готовим окружение (создаем папки)
    setup_environment()
    
    # 2. Создаем экземпляр нашего приложения
    app = PhraseWeaverApp()
    
    # 3. Запускаем его. Эта команда запускает цикл событий Kivy,
    # отрисовывает окно и ждет действий пользователя. Программа будет
    # работать до тех пор, пока пользователь не закроет окно.
    app.run()