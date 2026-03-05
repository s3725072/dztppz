# from operator import index
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import AsyncImage
from kivy.clock import Clock
# from api_client import MapsAPIClient
# from navigation_client import NavigationAPIClient
import threading
class SearchBar(BoxLayout):
    def init(self, **kwargs):
        super().init(**kwargs)
        self.size_hint = (None, None)
        self.size = (300, 40)
        self.padding = [6, 4]
        self.orientation = 'horizontal'

        with self.canvas.before:
            Color(0.75, 0.75, 0.75, 1)
            self.border = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[12]
            )

            Color(1, 1, 1, 1)
            self.bg = RoundedRectangle(
                pos=(self.x + 2, self.y + 2),
                size=(self.width - 4, self.height - 4),
                radius=[10]
            )

        self.bind(pos=self.update_bg, size=self.update_bg)

        self.search_input = TextInput(
            hint_text="Поиск мест...",
            multiline=False,
            size_hint_x=1,
            background_normal='',
            background_active='',
            background_color=(0, 0, 0, 0),
            foreground_color=(0, 0, 0, 1),
            cursor_color=(0, 0, 0, 1),
            padding=[10, 6, 10, 6],
            font_size='14sp'
        )

        self.add_widget(self.search_input)

    def update_bg(self, *args):
        self.border.pos = self.pos
        self.border.size = self.size
        self.bg.pos = (self.x + 2, self.y + 2)
        self.bg.size = (self.width - 4, self.height - 4)


class WhiteBar(AnchorLayout):
    def init(self, **kwargs):
        super().init(**kwargs)
        self.size_hint_y = None
        self.height = 80
        self.padding = 10

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        self.bind(pos=self.update_bg, size=self.update_bg)

        center_anchor = AnchorLayout(
            anchor_x='center',
            anchor_y='center',
            size_hint_x=1
        )

        button_container = BoxLayout(
            orientation='horizontal',
            spacing=50,
            size_hint=(None, None),
            size=(140, 60)
        )

        btn1 = Button(
            background_normal="navi.png",
            background_down="navi.png",
            size_hint=(None, None),
            size=(56, 43),
            border=(1, 1, 1, 1),
            background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1),
        )

        with btn1.canvas.after:
            Color(0, 0, 0, 1)
            btn1.border_line = Line(
                rounded_rectangle=(btn1.x, btn1.y, btn1.width, btn1.height, 10),
                width=0.5
            )
        btn1.bind(pos=self.update_border, size=self.update_border)

        btn2 = Button(
            background_normal="bests.png",
            background_down="bests.png",
            size_hint=(None, None),
            size=(56, 43),
            border=(1, 1, 1, 1),
            background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1)
        )
        with btn2.canvas.after:
            Color(0, 0, 0, 1)
            btn2.border_line = Line(
                rounded_rectangle=(btn2.x, btn2.y, btn2.width, btn2.height, 10),
                width=0.5
            )
        btn2.bind(pos=self.update_border, size=self.update_border)

        button_container.add_widget(btn1)
        button_container.add_widget(btn2)
        center_anchor.add_widget(button_container)
        self.add_widget(center_anchor)


def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

def update_border(self, instance, value):
    instance.border_line.rounded_rectangle = (
            instance.x, instance.y,
            instance.width, instance.height,
            10
        )


class MapDisplay(BoxLayout):
    

    def init(self, **kwargs):
        super().init(**kwargs)
        self.orientation = 'vertical'

        with self.canvas.before:
            Color(0.9, 0.9, 0.9, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.status_label = Label(
            text="Карта загружается...",
            size_hint_y=None,
            height=30,
            color=(0, 0, 0, 1),
            font_size='12sp'
        )

        self.add_widget(self.status_label)
        # Информация о навигации
        self.nav_label = Label(
            text="Навигационная сеть загружается...",
            size_hint_y=None,
            height=30,
            color=(0, 0, 0, 1),
            font_size='12sp'
        )
        self.add_widget(self.nav_label)
        # Информация о текущей локации
        self.location_label = Label(
            text="Текущая локация: неизвестна",
            size_hint_y=None,
            height=30,
            color=(0, 0, 0, 1),
            font_size='11sp'
        )
        self.add_widget(self.location_label)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def load_map_style(self, style_id=1):
        #Загрузить стиль карты из API
        app = App.get_running_app()

        def fetch_data():
            # Загружаем стиль карты
            map_style = app.maps_api.get_style(1)

            # Загружаем навигационную сеть
            nav_nodes = app.nav_api.get_nodes()

            # Получаем последнюю локацию
            last_location = app.nav_api.get_latest_location()

            Clock.schedule_once(
                lambda dt: self.on_data_loaded(map_style, nav_nodes, last_location), 0
            )

        threading.Thread(target=fetch_data, daemon=True).start()

    def on_data_loaded(self, map_style, nav_nodes, last_location):
        #Обработка загруженных данных
        if map_style:
            self.map_label.text = f"✓ Карта: {map_style.get('name', 'Неизвестно')}"
        else:
            self.map_label.text = "✗ Карта недоступна"

        if nav_nodes:
            node_count = nav_nodes.get('count', 0)
            self.nav_label.text = f"✓ Навигация: {node_count} узлов"
        else:
            self.nav_label.text = "✗ Навигация недоступна"

        if last_location:
            lat = last_location.get('latitude', 0)
            lon = last_location.get('longitude', 0)
            self.location_label.text = f"✓ Локация: {lat:.4f}, {lon:.4f}"
        else:
            self.location_label.text = "✗ Локация не найдена"

class MainScreen(Screen):
    def init(self, **kwargs):
        super().init(**kwargs)

        root = BoxLayout(orientation='vertical')

        top_bar = AnchorLayout(
            anchor_x='center',
            anchor_y='top',
            size_hint_y=None,
            height=100
        )

        top_bar.add_widget(SearchBar())
        root.add_widget(top_bar)

        # Добавляем виджет карты
        self.map_display = MapDisplay()
        root.add_widget(self.map_display)
        white_bar = WhiteBar()
        root.add_widget(white_bar)
        self.bind_white_bar_buttons(white_bar)
        self.add_widget(root)

    def on_enter(self):
        #Вызывается при входе на экран
        self.map_display.load_all_data()

    def bind_white_bar_buttons(self, white_bar):
        for child in white_bar.walk():
            if isinstance(child, Button):
                if child.background_normal == "bests.png":
                    child.bind(on_press=self.go_to_new_window)

    def go_to_new_window(self, instance):
        App.get_running_app().sm.current = 'Популярные маршруты'


class RoundedButton(Button):
    def init(self, **kwargs):
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        kwargs.setdefault('color', (0, 0, 0, 1))

        super().init(**kwargs)

        with self.canvas.after:
            Color(0, 0, 0, 1)
            self.border_line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 10), width=0.5)

        self.bind(pos=self.update_border, size=self.update_border)

    def update_bg(self, instance, value):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def update_border(self, instance, value):
        instance.border_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 10)


class RouteWindow(Screen):
    def init(self, **kwargs):
        super().init(**kwargs)
        self.current_route_name = None
        self.layout = BoxLayout(orientation='vertical', padding=20)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.title_label = Label(
            text=" ",
            font_size=14,
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=50,
            bold=True
        )

        self.layout.add_widget(self.title_label)

        self.route_info = Label(
            text="",
            font_size=12,
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=100,
            halign='left',
            valign='top'
        )
        self.route_info.bind(size=self.route_info.setter('text_size'))
        self.layout.add_widget(self.route_info)

        float_layout = FloatLayout()

        btn_back = Button(
            background_normal="exit.png",
            background_down="exit.png",
            size_hint=(None, None),
            size=(60, 53),
            pos=(730, 550),
            background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1)
        )

        btn_back.bind(
            on_press=lambda x: setattr(App.get_running_app().sm, 'current', 'Популярные маршруты')
        )

        float_layout.add_widget(btn_back)
        self.layout.add_widget(float_layout)

        self.add_widget(self.layout)

    def set_route(self, route_id):
        self.title_label.text = f"Информация о маршруте '{route_id}' "
        self.load_route_data(route_id)

    def load_route_data(self, route_id):
        #Загрузить данные маршрута из API
        app = App.get_running_app()

        # Примерные координаты для демонстрации
        routes_coords = {
            "Красная площадь": (55.7558, 37.6173, 55.7520, 37.6175),
            "Парк Сокольники": (55.7904, 37.6707, 55.7950, 37.6750),
            "ВДНХ": (55.8304, 37.6278, 55.8350, 37.6320),
            "Останкино": (55.8196, 37.6119, 55.8240, 37.6160),
            "Зарядье": (55.7510, 37.6280, 55.7550, 37.6320),
        }

        if route_id in routes_coords:
            coords = routes_coords[route_id]

            def fetch_route():
                route_data = app.api_client.get_map_with_route(
                    start_lat=coords[0],
                    start_lon=coords[1],
                    end_lat=coords[2],
                    end_lon=coords[3],
                    routing_type="fastest"
                )
                if route_data:
                    Clock.schedule_once(
                        lambda dt: self.display_route(route_data), 0
                    )

            threading.Thread(target=fetch_route, daemon=True).start()

    def display_route(self, route_data):
        #Отобразить данные маршрута
        summary = route_data.get('summary', {})
        distance = summary.get('distance_meters', 0) / 1000
        duration = summary.get('duration_seconds', 0) / 60
        steps = route_data.get('steps', [])

        self.route_info.text = (
            f"Расстояние: {distance:.2f} км\n"
            f"Время в пути: {duration:.1f} мин\n"
            f"Шагов: {summary.get('steps_count', 0)}"
        )

def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


class NewWindowScreen(Screen):
    def init(self, **kwargs):
        super().init(**kwargs)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        main_layout = BoxLayout(orientation='vertical', padding=[10, 10], spacing=10)

        top_bar = BoxLayout(size_hint_y=None, height=50)

        f_l = FloatLayout()

        btn_back = Button(
            background_normal="exit.png",
            background_down="exit.png",
            size_hint=(None, 1),
            pos=(730, 550),
            width=60,
            background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1)
        )

        btn_back.bind(
            on_press=lambda x: setattr(App.get_running_app().sm, 'current', 'Карта')
        )

        title_label = Label(
            text="Популярные направления",
            color=(0, 0, 0, 1),
            font_size=20,
            pos=(0, 550),
            bold=True
        )

        f_l.add_widget(title_label)
        f_l.add_widget(btn_back)
        top_bar.add_widget(f_l)
        main_layout.add_widget(top_bar)

        content_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        content_layout.bind(minimum_height=self.content_layout.setter('height'))

        des = ["Красная площадь", "Парк Сокольники", "ВДНХ", "Останкино", "Зарядье"]

        for i in range(0, len(des)):
            item = RoundedButton(
                text=f"Маршрут {des[i]}",
                size_hint_y=None,
                height=100,
            )

            def on_route_press(instance, rid=des[i]):
                app = App.get_running_app()
                route_screen = app.sm.get_screen('route_window')
                route_screen.set_route(rid)
                app.sm.current = 'route_window'

            item.bind(on_press=on_route_press)
            content_layout.add_widget(item)

        scroll_view = ScrollView(size_hint=(1, 1), bar_color=(0.6, 0.6, 0.6, 1),
                                 bar_inactive_color=(0.8, 0.8, 0.8, 0.8))
        scroll_view.add_widget(content_layout)

        main_layout.add_widget(scroll_view)
        self.add_widget(main_layout)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


class MyApp(App):
    def build(self):
        # Инициализация API клиента
        self.api_client = MapsAPIClient(base_url="http://localhost:8000")
        self.nav_api = NavigationAPIClient(base_url="http://localhost:8001")
        # Проверка подключения
        maps_ok = self.maps_api.health_check() is not None
        nav_ok = self.nav_api.health_check() is not None
        if maps_ok:
            print("✓ Подключение к API успешно")
        else:
            print("API недоступен")
        if nav_ok:
            print("✓ Подключение к API успешно")
        else:
            print("API недоступен")

        self.sm = ScreenManager()
        self.sm.add_widget(MainScreen(name='Карта'))
        self.sm.add_widget(NewWindowScreen(name='Популярные маршруты'))
        self.sm.add_widget(RouteWindow(name='route_window'))
        return self.sm

    def on_stop(self):
        #Закрыть соединение при выходе
        self.maps_api.close()
        self.nav_api.close()

if __name__ == 'main':
    MyApp().run()  

# import requests
# from typing import Optional, List, Dict
# from datetime import datetime

# class MapsAPIClient:
#     #Клиент для взаимодействия с Maps API
#     def init(self, base_url: str = "http://localhost:8000"):
#         self.base_url = base_url
#         self.session = requests.Session()

#     def get_styles(self) -> Optional[List[Dict]]:
#         #Получить список всех стилей карт
#         try:
#             response = self.session.get(f"{self.base_url}/styles")
#             response.raise_for_status()
#             return response.json().get('items', [])
#         except requests.RequestException as e:
#             print(f"Ошибка получения стилей: {e}")
#             return None

#     def get_style(self, style_id: int) -> Optional[Dict]:
#         #Получить конкретный стиль по ID
#         try:
#             response = self.session.get(f"{self.base_url}/styles/{style_id}")
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка получения стиля {style_id}: {e}")
#             return None

#     def get_tile_url(self, z: int, x: int, y: int) -> str:
#         #Получить URL векторного тайла
#         return f"{self.base_url}/tiles/{z}/{x}/{y}.mvt"

#     def get_map_with_route(
#             self,
#             start_lat: float,
#             start_lon: float,
#             end_lat: float,
#             end_lon: float,
#             routing_type: str = "fastest",
#             style_id: int = 1
#     ) -> Optional[Dict]:
#         #Получить карту с маршрутом
#         try:
#             params = {
#                 "start_lat": start_lat,
#                 "start_lon": start_lon,
#                 "end_lat": end_lat,
#                 "end_lon": end_lon,
#                 "routing_type": routing_type,
#                 "style_id": style_id
#             }
#             response = self.session.get(
#                 f"{self.base_url}/map-with-route",
#                 params=params
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка получения маршрута: {e}")
#             return None

#     def save_location(
#             self,
#             latitude: float,
#             longitude: float,
#             accuracy: float,
#             altitude: Optional[float] = None,
#             speed: Optional[float] = None
#     ) -> Optional[Dict]:
#         #Сохранить GPS координаты
#         try:
#             data = {
#                 "latitude": latitude,
#                 "longitude": longitude,
#                 "accuracy": accuracy,
#                 "altitude": altitude,
#                 "speed": speed,
#                 "timestamp": datetime.now().isoformat()
#             }
#             response = self.session.post(
#                 f"{self.base_url}/location",
#                 json=data
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка сохранения локации: {e}")
#             return None

#     def get_location_history(
#             self,
#             limit: int = 100,
#             offset: int = 0
#     ) -> Optional[List[Dict]]:
#         #Получить историю локаций
#         try:
#             params = {"limit": limit, "offset": offset}
#             response = self.session.get(
#                 f"{self.base_url}/location/history",
#                 params=params
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка получения истории: {e}")
#             return None

#     def health_check(self) -> Optional[Dict]:
#         #Проверить состояние API
#         try:
#             response = self.session.get(f"{self.base_url}/health")
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"API недоступен: {e}")
#             return None

#     def close(self):
#         #Закрыть сессию
#         self.session.close()-api_client


# class NavigationAPIClient:
#     #Клиент для взаимодействия с Navigation API
#     def init(self, base_url: str = "http://localhost:8001"):
#         self.base_url = base_url
#         self.session = requests.Session()
#     def save_location(
#             self,
#             latitude: float,
#             longitude: float,
#             accuracy: float,
#             altitude: Optional[float] = None,
#             speed: Optional[float] = None
#     ) -> Optional[Dict]:
#         #Сохранить GPS координаты
#         try:
#             data = {
#                 "latitude": latitude,
#                 "longitude": longitude,
#                 "accuracy": accuracy,
#                 "altitude": altitude,
#                 "speed": speed,
#                 "timestamp": datetime.now().isoformat()
#             }
#             response = self.session.post(
#                 f"{self.base_url}/location",
#                 json=data
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка сохранения локации: {e}")
#             return None

#     def get_location_history(
#             self,
#             limit: int = 100,
#             offset: int = 0
#     ) -> Optional[Dict]:
#         #Получить историю перемещений
#         try:
#             params = {"limit": limit, "offset": offset}
#             response = self.session.get(
#                 f"{self.base_url}/location/history",
#                 params=params
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка получения истории: {e}")
#             return None

#     def get_latest_location(self) -> Optional[Dict]:
#         #Получить последнюю известную позицию
#         try:
#             response = self.session.get(f"{self.base_url}/location/latest")
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка получения последней локации: {e}")
#             return None

#     def clear_location_history(self) -> Optional[Dict]:
#         #Очистить всю историю перемещений
#         try:
#             response = self.session.delete(f"{self.base_url}/location/history")
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка очистки истории: {e}")
#             return None

#     def get_location_stats(self) -> Optional[Dict]:
#         #Получить статистику по локациям
#         try:
#             response = self.session.get(f"{self.base_url}/location/stats")
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка получения статистики: {e}")
#             return None

#     def calculate_route(self, start_lat: float, start_lon: float,
#             end_lat: float,
#             end_lon: float,
#             routing_type: str = "fastest") -> Optional[Dict]:
#         #Построить маршрут между двумя точками
#         try:
#             data = {
#                 "start": {"lat": start_lat, "lon": start_lon},
#                 "end": {"lat": end_lat, "lon": end_lon},
#                 "routing_type": routing_type
#             }
#             response = self.session.post(
#                 f"{self.base_url}/api/v1/route",
#                 json=data
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка построения маршрута: {e}")
#             return None

# def calculate_route_from_current(
#             self,
#             end_lat: float,
#             end_lon: float,
#             routing_type: str = "fastest"
#     ) -> Optional[Dict]:
#         #Построить маршрут от текущей позиции
#         try:
#             params = {"routing_type": routing_type}
#             data = {"lat": end_lat, "lon": end_lon}
#             response = self.session.post(
#                 f"{self.base_url}/api/v1/route/from-current",
#                 params=params,
#                 json=data
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка построения маршрута: {e}")
#             return None

# def get_route_with_map(
#             self,
#             start_lat: float,
#             start_lon: float,
#             end_lat: float,
#             end_lon: float,
#             routing_type: str = "fastest"
#     ) -> Optional[Dict]:
#         #Получить маршрут с данными карты
#         try:
#             params = {
#                 "start_lat": start_lat,
#                 "start_lon": start_lon,
#                 "end_lat": end_lat,
#                 "end_lon": end_lon,
#                 "routing_type": routing_type
#             }
#             response = self.session.get(
#                 f"{self.base_url}/api/v1/route-with-map",
#                 params=params
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка получения маршрута с картой: {e}")
#             return None


# def get_nodes(self) -> Optional[Dict]:
#         #Получить все узлы навигационной сети
#         try:
#             response = self.session.get(f"{self.base_url}/api/v1/nodes")
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка получения узлов: {e}")
#             return None

# def get_nearest_node(self, lat: float, lon: float) -> Optional[Dict]:
#         #Найти ближайший узел к координатам
#         try:
#             params = {"lat": lat, "lon": lon}
#             response = self.session.get(
#                 f"{self.base_url}/api/v1/nearest",
#                 params=params
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка поиска ближайшего узла: {e}")
#             return None

# def create_node(
#             self,
#             lat: float,
#             lon: float,
#             name: Optional[str] = None,
#             node_type: str = "intersection"
#     ) -> Optional[Dict]:
#         #Создать новый узел
#         try:
#             data = {
#                 "lat": lat,
#                 "lon": lon,
#                 "name": name,
#                 "node_type": node_type
#             }
#             response = self.session.post(
#                 f"{self.base_url}/api/v1/nodes",
#                 json=data
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка создания узла: {e}")
#             return None

# def get_edges(self, limit: int = 100, offset: int = 0) -> Optional[Dict]:
#         #Получить список рёбер
#         try:
#             params = {"limit": limit, "offset": offset}
#             response = self.session.get(
#                 f"{self.base_url}/api/v1/edges",
#                 params=params
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка получения рёбер: {e}")
#             return None
        
# def create_edge(self,from_node: int,to_node: int, distance: Optional[float] = None,
#             walk_time: Optional[float] = None,
#             road_type: str = "sidewalk",
#             is_bidirectional: bool = True
#     ) -> Optional[Dict]:
#         #Создать новое ребро
#         try:
#             data = {
#                 "from_node": from_node,
#                 "to_node": to_node,
#                 "distance": distance,
#                 "walk_time": walk_time,
#                 "road_type": road_type,
#                 "is_bidirectional": is_bidirectional
#             }
#             response = self.session.post(
#                 f"{self.base_url}/api/v1/edges",
#                 json=data
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка создания ребра: {e}")
#             return None

# def health_check(self) -> Optional[Dict]:
#         #Проверить состояние API
#         try:
#             response = self.session.get(f"{self.base_url}/api/v1/health")
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Navigation API недоступен: {e}")
#             return None

# def get_info(self) -> Optional[Dict]:
#         #Получить информацию об API
#         try:
#             response = self.session.get(f"{self.base_url}/")
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Ошибка получения информации: {e}")
#             return None

# def close(self):
#         #Закрыть сессию
#         self.session.close()-navigation_client
















