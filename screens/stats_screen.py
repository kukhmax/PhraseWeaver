from kivy.clock import mainthread
from kivy.utils import get_color_from_hex # Нам все еще может понадобиться для других вещей, так что оставим
from kivymd.app import MDApp

from kivy_garden.graph import Graph, LinePlot

from kivymd.uix.screen import MDScreen


class StatsScreen(MDScreen):
    """
    Экран для отображения статистики и прогресса пользователя.
    """

    def on_enter(self, *args):
        """Вызывается при входе на экран. Запускает обновление данных."""
        self.update_stats()
        self.plot_review_history()

    def update_stats(self):
        """Обновляет числовые показатели на карточках."""
        app = MDApp.get_running_app()
        db_manager = app.db_manager
        
        learned_count = db_manager.count_learned_cards()
        streak_count = db_manager.get_study_streak()

        self.ids.learned_cards_label.text = str(learned_count)
        self.ids.streak_label.text = str(streak_count)

    def plot_review_history(self):
        """

        Запрашивает историю повторений и строит на ее основе график.
        """
        app = MDApp.get_running_app()
        db_manager = app.db_manager
        
        reviews_per_day = db_manager.get_reviews_per_day(days=7)
        
        graph_container = self.ids.graph_container
        graph_container.clear_widgets()

        if not reviews_per_day or not any(reviews_per_day.values()):
            # Если данных нет, или все значения - нули, не рисуем график
            return

        graph = Graph(
            xlabel='Дата',
            ylabel='Повторения',
            x_ticks_minor=0,
            x_ticks_major=1,
            y_ticks_major=max(1, int(max(reviews_per_day.values()) / 5)), # Динамический шаг
            y_grid_label=True,
            x_grid_label=True,
            padding=10,
            x_grid=True,
            y_grid=True,
            xmin=0,
            xmax=len(reviews_per_day) - 1,
            ymin=0,
            ymax=max(reviews_per_day.values())
        )

        sorted_dates = sorted(reviews_per_day.keys())
        points = [(i, reviews_per_day[date]) for i, date in enumerate(sorted_dates)]
        
        # --- ИСПРАВЛЕНО ОКОНЧАТЕЛЬНО ---
        # Передаем цвет напрямую, без get_color_from_hex
        plot = LinePlot(
            color=app.theme_cls.primary_color, 
            line_width=2
        )
        plot.points = points
        
        graph.x_ticks_labels = [date.split('-')[-1] for date in sorted_dates]
        
        graph.add_plot(plot)
        graph_container.add_widget(graph)