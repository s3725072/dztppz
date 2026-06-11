# from operator import index
from importlib.resources import path
from platform import node
import json
from unittest import result
from kivy_garden.mapview import MapView, MapMarker,MapLayer
from tracemalloc import start
from weakref import ref
from kivy.uix.popup import Popup
from kivy import app
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle,Ellipse
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import AsyncImage
from kivy.clock import Clock
from ray import nodes, worker
import requests
import sqlite3
from api_client import MapsAPIClient
from navigation_client import NavigationAPIClient
from area_api import calculate_area_km2
import math
import asyncio
from places_api import find_nearby, filter_by_metro
from route_api import init_database,find_nearest_node, build_graph, dijkstra,get_db, haversine_distance,get_route_steps, build_route_geometry




import threading
class SearchBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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



    # def on_search_end(self, text):             
    #     app = App.get_running_app()
    #     result = app.nav_api.geocode(text)    добавление поиска через Search Bar

    #     if result:
    #         app.selected_end = {
    #             "lat": result["lat"],
    #             "lon": result["lon"]
    #         }
    #         print("END:", app.selected_end)

    
    # def on_search_start(self, text):
    #     app = App.get_running_app()
    #     result = app.nav_api.geocode(text)

    #     if result:
    #         app.selected_start = {
    #             "lat": result["lat"],
    #             "lon": result["lon"]
    #         }
    #         print("start:", app.selected_start)

    
    # def on_enter(self, instance):
    #     text = instance.text.strip()

    #     if not text:
    #         return

    #     if self.mode == "start":
    #         self.on_search_start(text)
    #     else:
    #         self.on_search_end(text)

class WhiteBar(AnchorLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 80
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size,radius=[10])   
        
        self.bind(pos=self.update_bg, size=self.update_bg)  

        center_anchor=AnchorLayout(anchor_x='center', anchor_y='center',size_hint_x=1)

        button_container = BoxLayout(orientation='horizontal', spacing=50, size_hint=(None, None), size=(140, 60))

        btn1=Button(background_normal="navi.png", background_down="navi.png", size_hint=(None, None), size=(56, 43), 
         border=(1,1,1,1),background_color=(1, 1, 1, 1), color=(0, 0, 0, 1))
        
        with btn1.canvas.after:
            Color(0,0,0,1)
            btn1.border_line=Line(rounded_rectangle=(btn1.x, btn1.y, btn1.width, btn1.height, 10), width=0.5)

        btn1.bind(pos=self.update_button_border, size=self.update_button_border)

        btn2=Button(background_normal="bests.png", background_down="bests.png", size_hint=(None, None), size=(56, 43),border=(1,1,1,1), background_color=(1, 1, 1, 1), color=(0, 0, 0, 1))
        
        with btn2.canvas.after:
            Color(0,0,0,1)
            btn2.border_line=Line(rounded_rectangle=(btn2.x, btn2.y, btn2.width, btn2.height, 10), width=0.5)
        btn2.bind(pos=self.update_button_border, size=self.update_button_border)

                

        button_container.add_widget(btn1)
        button_container.add_widget(btn2)
        
        center_anchor.add_widget(button_container)
        self.add_widget(center_anchor)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
    
    def update_button_border(self, instance, *args):
        instance.border_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 10)


class RoundedButton(Button):
    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        with self.canvas.after:
            Color(0, 0, 0, 1)
            self.border_line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 10), width=0.5)

        self.bind(pos=self.update_border, size=self.update_border)

    def update_bg(self, instance, value):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def update_border(self, instance, value):
        instance.border_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 10)


class MyMapView(MapView):

    def on_touch_down(self, touch):
        app = App.get_running_app()

        if not getattr(app, "selecting_route", False):
            return super().on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        # координаты места нажатия
        lat, lon = self.get_latlon_at(*touch.pos)

        if app.selected_start is None:
            app.selected_start = {"lat": lat, "lon": lon}

            marker_a = MapMarker(lat=lat, lon=lon)
            self.add_marker(marker_a)

            print("A выбрана")
            return True

        elif app.selected_end is None:
            app.selected_end = {"lat": lat, "lon": lon}

            marker_b = MapMarker(lat=lat, lon=lon)
            self.add_marker(marker_b)

            print("B выбрана")

            app.sm.current = "route_window"
            return True

        return super().on_touch_down(touch)



class RouteLineLayer(MapLayer):

    def __init__(self, mapview, route_points, **kwargs):
        super().__init__(**kwargs)
        self.mapview = mapview
        self.route_points = route_points

    def reposition(self):

        self.canvas.clear()

        if len(self.route_points) < 2:
            return

        points = []

        for lat, lon in self.route_points:

            x, y = self.mapview.get_window_xy_from(
                lat,
                lon,
                self.mapview.zoom
            )

            points.extend([x, y])

        with self.canvas:
            Color(1, 0, 0, 1)
            Line(points=points, width=3)


class CircleMarker(MapMarker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.size = (20, 20)

        with self.canvas.after:
            Color(1, 0, 0, 0.5)
            self.circle = Ellipse(size=self.size)

        self.bind(pos=self.update_circle, size=self.update_circle)


    def update_circle(self, *args):
        
        self.circle.pos = (
            self.center_x - self.circle.size[0]  / 2,
            self.center_y - self.circle.size[1] / 2
        )


class MapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ext_search_mode = False

        layout = FloatLayout()


        self.map = MyMapView(
            lat=55.751244,
            lon=37.618423,
            zoom=12,
            size_hint=(1, 1)
        )

        self.area_points = []
        
        self.map_label = Label(
            text="",
            size_hint=(None, None),
            size=(300, 50),
            pos_hint={"x": 0.02, "y": 0.9},
            color=(0, 0, 0, 1)
            )

        layout.add_widget(self.map)
        layout.add_widget(self.map_label)

        
        self.ext_search=RoundedButton(
            text="Расширенный поиск",
            size_hint=(None, None),
            size=(150, 40),
            pos_hint={"x": 0.02, "y": 0.8},
            background_normal='',
            background_down='',
            background_color=(1,0.65,1,1),
            color=(1,1,1,1)
        )
        
        layout.add_widget(self.ext_search)

        self.ext_search.bind(on_press=self.start_ext_search)
        

        self.add_widget(layout)
        
        self.place_markers = []

    def start_ext_search(self, instance):
        self.ext_search_mode = True

    
    def add_touch_marker(self, lat, lon):

        self.touch_marker = CircleMarker(
            lat=lat,
            lon=lon
        )

        self.map.add_widget(self.touch_marker)




    def search_touch(self, touch):
        handled = super().on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return handled


        if not self.ext_search_mode:
            return handled

        lat, lon = self.get_latlon_at(*touch.pos)

        Clock.schedule_once(lambda dt: self.add_touch_marker(lat, lon))

        threading.Thread(
            target=self.search_places,
            args=(lat, lon),
            daemon=True
        ).start()

        return True



    def search_places(self, lat, lon):
        try:
            result = find_nearby(lat, lon, radius_km=5.0)

            places = result["result"]["items"]

    
            places = filter_by_metro(places)

    
            places.sort(key=lambda x: (x.get("metro") or "", x.get("distance", 999)))

            Clock.schedule_once(lambda dt: self.show_places_on_map(places), 0)    
        except Exception as e:
            print("Ошибка поиска:", e)

    
    def show_places_on_map(self, places):


        for place in places:
            marker = MapMarker(
                lat=place["lat"],
                lon=place["lon"]
            )
            self.add_widget(marker)
            self.place_markers.append(marker)

  


    def on_touch_down(self, touch):
        
        handled = super().on_touch_down(touch)

        if not self.map.collide_point(*touch.pos):
                return handled

        
        if touch.is_double_tap:
                lat, lon = self.map.get_latlon_at(*touch.pos)

                self.area_points.append({"lat": lat, "lon": lon})

                if len(self.area_points) == 2:
                    Clock.schedule_once(lambda dt: self.open_shape_popup(), 0)

                return True
        return handled

  
    def open_shape_popup(self):
            layout = BoxLayout(orientation='vertical')

            btn_circle = Button(text="Круг")
            btn_square = Button(text="Прямоугольник")

            layout.add_widget(btn_circle)
            layout.add_widget(btn_square)

            popup = Popup(
            title="Выберите фигуру",
            content=layout,
            size_hint=(0.5, 0.5)
        )

            btn_circle.bind(on_press=lambda x: self.calculate_area("circle", popup))
            btn_square.bind(on_press=lambda x: self.calculate_area("square", popup))

            popup.open()

   
    def calculate_area(self, shape, popup):
        popup.dismiss()

        p1, p2 = self.area_points

        dx = (p1["lon"] - p2["lon"]) * 111000
        dy = (p1["lat"] - p2["lat"]) * 111000

        radius_m = (dx**2 + dy**2) ** 0.5

        area = calculate_area_km2(radius_m, shape)

        self.map_label.text = f"Площадь ({shape}): {area:.4f} км²"

        self.area_points = []

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


class RouteScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.route_layer = None

        layout = BoxLayout(orientation="vertical")

        self.map = MyMapView(
            lat=55.751244,
            lon=37.618423,
            zoom=12
        )

        self.nav_label = Label(
            text="",
            size_hint=(None, None),
            size=(300, 50),
            pos_hint={"x": 0.02, "y": 0.9},
            color=(1, 1, 1, 1)
            )


        self.route_info = Label(
            text=" ",
            size_hint=(1, None),
            height=120,
            markup=True
        )

        scroll = ScrollView(size_hint=(1, None), height=120)
        scroll.add_widget(self.route_info)

        layout.add_widget(self.map)
        layout.add_widget(self.nav_label)
        layout.add_widget(scroll)

        btn_go = Button(text="GO", size_hint=(1, 0.1))
        btn_go.bind(on_press=self.build_route)
        layout.add_widget(btn_go)

        self.add_widget(layout)

        self.route_info.bind(on_ref_press=self.on_ref_press)



    def build_route(self, instance):

        app = App.get_running_app()

        start = app.selected_start
        end = app.selected_end

        def worker():
            try:
                start_lat = start["lat"]
                start_lon = start["lon"]

                end_lat = end["lat"]
                end_lon = end["lon"]

                url = (
                    f"https://router.project-osrm.org/route/v1/driving/"
                    f"{start_lon},{start_lat};"
                    f"{end_lon},{end_lat}"
                    f"?overview=full&geometries=geojson"
                )

                response = requests.get(url, timeout=10)

                if response.status_code != 200:
                    print("OSRM ERROR:", response.status_code)
                    return

                data = response.json()

                if not data.get("routes"):
                    print("Маршрут не найден")
                    return

                route = data["routes"][0]

                distance_m = route["distance"]
                duration_s = route["duration"]

                coordinates = route["geometry"]["coordinates"]

                route_points = [
                    (lat, lon)
                    for lon, lat in coordinates
                ]

                def update_ui(dt):
                    self.nav_label.text = (
                        f"Расстояние: {distance_m / 1000:.2f} км\n"
                        f"Время: {duration_s / 60:.1f} мин"
                    )

                    if hasattr(self, "route_layer") and self.route_layer:
                        self.map.remove_layer(self.route_layer)

                    self.route_layer = RouteLineLayer(
                        self.map,
                        route_points
                    )

                    self.map.add_layer(self.route_layer)

                Clock.schedule_once(update_ui)

            except Exception as e:
                print("Ошибка маршрута:", e)

        threading.Thread(
            target=worker,
            daemon=True
        ).start()


#---------------------------------------------------



    # def build_route(self, instance):
    #     app = App.get_running_app()
        
    #     start = app.selected_start
    #     end = app.selected_end

    #     print(start)
    #     print(end)

    #     def distance(lat1, lon1, lat2, lon2):
    #         return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5

    #     dist = distance(
    #         start["lat"],
    #         start["lon"],
    #         end["lat"],
    #         end["lon"]
    #     )
        
       

    #     self.nav_label.text = f"Расстояние: {dist:.4f} (условные единицы)"

    #     def generate_intermediate_nodes(start, end):

        

    #         mid1 = {
    #              "lat": start["lat"] + 0.001,
    #              "lon": start["lon"]
    #         }

    #         mid2 = {
    #             "lat": start["lat"] + 0.001,
    #             "lon": end["lon"]
    #         }

    #         return [
    #             start,
    #             mid1,
    #             mid2,
    #             end
    #         ]

        # def add_generated_nodes_to_db(node_list):

        #     node_ids = []

        #     with get_db() as conn:
        #         conn.row_factory = sqlite3.Row
        #         cursor = conn.cursor()

        #         prev_node_id = None
        #         prev_lat = None
        #         prev_lon = None

        #         for node in node_list:

        #             lat = node["lat"]
        #             lon = node["lon"]

        #             cursor.execute(
        #                 """
        #                 SELECT id
        #                 FROM nodes
        #                 WHERE ABS(lat - ?) < 0.0000001
        #                 AND ABS(lon - ?) < 0.0000001
        #                 """,
        #                 (lat, lon)
        #             )

        #             row = cursor.fetchone()

        #             if row:
        #                 node_id = row["id"]
        #             else:
        #                 cursor.execute(
        #                     """
        #                     INSERT INTO nodes(lat, lon)
        #                     VALUES (?, ?)
        #                     """,
        #                     (lat, lon)
        #                 )
        #             node_id = cursor.lastrowid

        #             node_ids.append(node_id)

        #             if prev_node_id is not None:

        #                 dist = haversine_distance(
        #                     prev_lat,
        #                     prev_lon,
        #                     lat,
        #                     lon
        #                 )

        #                 walk_time = dist / 1.4

        #                 cursor.execute(
        #                     """
        #                     SELECT id
        #                     FROM edges
        #                     WHERE from_node=?
        #                     AND to_node=?
        #                     """,
        #                     (prev_node_id, node_id)
        #                 )

        #                 edge_exists = cursor.fetchone()

        #                 if not edge_exists:

        #                     cursor.execute(
        #                         """
        #                         INSERT INTO edges
        #                         (
        #                             from_node,
        #                             to_node,
        #                             distance,
        #                             walk_time,
        #                             is_bidirectional
        #                         )
        #                         VALUES (?, ?, ?, ?, ?)
        #                         """,
        #                         (
        #                             prev_node_id,
        #                             node_id,
        #                             dist,
        #                             walk_time,
        #                             1
        #                         )
        #                     )

        #                     cursor.execute(
        #                     """
        #                     INSERT INTO edges
        #                     (
        #                         from_node,
        #                         to_node,
        #                         distance,
        #                         walk_time,
        #                         is_bidirectional
        #                     )
        #                     VALUES (?, ?, ?, ?, ?)
        #                     """,
        #                     (
        #                         node_id,
        #                         prev_node_id,
        #                         dist,
        #                         walk_time,
        #                         1
        #                     )
        #                 )

        #             prev_node_id = node_id
        #             prev_lat = lat
        #             prev_lon = lon

        #         conn.commit()

        #     return node_ids


        # gen_in=generate_intermediate_nodes(start, end)

        # print(f"Generated intermediate nodes: {gen_in}")

        # nodes=add_generated_nodes_to_db(gen_in)

        # print(f"Generated node IDs: {nodes}")


#------------------------------------------------------

        # def add_generated_nodes_to_db(node_list):

        #     node_ids = []

        #     with get_db() as conn:
        #         conn.row_factory = sqlite3.Row
        #         cursor = conn.cursor()

        #         prev_node_id = None
        #         prev_lat = None
        #         prev_lon = None

        #         for node in node_list:

        #             lat = node["lat"]
        #             lon = node["lon"]

        #             cursor.execute(
        #             """
        #             SELECT id
        #             FROM nodes
        #             WHERE ABS(lat - ?) < 0.0000001
        #             AND ABS(lon - ?) < 0.0000001
        #             """,
        #             (lat, lon)
        #             )

        #             row = cursor.fetchone()

        #             if row:
        #                 node_id = row["id"]
        #             else:
        #                 cursor.execute(
        #                  "INSERT INTO nodes (lat, lon) VALUES (?, ?)",
        #                 (lat, lon)
        #                 )
        #                 node_id = cursor.lastrowid

        #             node_ids.append(node_id)

        #             if prev_node_id is not None:

        #                 dist = haversine_distance(
        #                     prev_lat,
        #                     prev_lon,
        #                     lat,
        #                     lon
        #                 )

        #             walk_time = dist / 1.4

        #             cursor.execute("""
        #                 SELECT 1
        #                 FROM edges
        #                 WHERE from_node = ?
        #                 AND to_node = ?
        #                 """, (prev_node_id, node_id))

        #             if not cursor.fetchone():

        #                 cursor.execute(
        #                     """
        #                     INSERT INTO edges
        #                     (
        #                         from_node,
        #                         to_node,
        #                         distance,
        #                         walk_time,
        #                         is_bidirectional
        #                     )
        #                     VALUES (?, ?, ?, ?, ?)
        #                     """,
        #                     (
        #                         prev_node_id,
        #                         node_id,
        #                         dist,
        #                         walk_time,
        #                         1
        #                     )
        #                 )

        #                 cursor.execute(
        #                     """
        #                     INSERT INTO edges
        #                     (
        #                         from_node,
        #                         to_node,
        #                         distance,
        #                         walk_time,
        #                         is_bidirectional
        #                     )
        #                     VALUES (?, ?, ?, ?, ?)
        #                     """,
        #                     (
        #                         node_id,
        #                         prev_node_id,
        #                         dist,
        #                         walk_time,
        #                         1
        #                     )
        #                 )

        #         prev_node_id = node_id
        #         prev_lat = lat
        #         prev_lon = lon

        #     conn.commit()

        #     return node_ids


        # def add_generated_nodes_to_db(node_list):
   
        #     node_ids = []
        #     with get_db() as conn:
        #         conn.row_factory = sqlite3.Row
        #         cursor = conn.cursor()

        #         prev_node_id = None
        #         prev_lat, prev_lon = None, None

        #         for node in node_list:
        #             lat, lon = node["lat"], node["lon"]
        #     # ищем существующий узел
        #             cursor.execute('SELECT id FROM nodes WHERE lat=? AND lon=?', (lat, lon))
        #             row = cursor.fetchone()
        #             if row:
        #                 node_id = row["id"]
        #             else:
        #                 cursor.execute('INSERT INTO nodes (lat, lon) VALUES (?, ?)', (lat, lon))
        #                 node_id = cursor.lastrowid

        #             node_ids.append(node_id)

        #     # создаем ребро с предыдущим узлом
        #             if prev_node_id is not None:
        #                 dist = haversine_distance(prev_lat, prev_lon, lat, lon)
        #                 walk_time = dist / 1.4
        #                 cursor.execute(
        #                 'INSERT OR IGNORE INTO edges (from_node,to_node,distance,walk_time,is_bidirectional) VALUES (?, ?, ?, ?, ?)',
        #                 (prev_node_id, node_id, dist, walk_time, 1)
        #                 )
        #                 cursor.execute(
        #                 'INSERT OR IGNORE INTO edges (from_node,to_node,distance,walk_time,is_bidirectional) VALUES (?, ?, ?, ?, ?)',
        #                 (node_id, prev_node_id, dist, walk_time, 1)
        #                 )

        #             prev_node_id = node_id
        #             prev_lat, prev_lon = lat, lon

        #             conn.commit()

        #     return node_ids    



            # def generate_intermediate_nodes(start, end):
    
        #     nodes = [start]

        #     for i in range(1, num_points+1):
        #         frac = i / (num_points+1)
        #         lat = start["lat"] + (end["lat"] - start["lat"]) * frac
        #         lon = start["lon"] + (end["lon"] - start["lon"]) * frac
        #         nodes.append({"lat": lat, "lon": lon})

        #     nodes.append(end)
        #     return nodes


#--------------------------------------


    #     def worker():
    #         init_database()

    #         nodes =generate_intermediate_nodes(start, end)
    #         node_ids = add_generated_nodes_to_db(nodes)

    #         with get_db() as conn:
    #             cursor = conn.cursor()
    #             cursor.execute('SELECT id FROM nodes WHERE lat=? AND lon=?', (start["lat"], start["lon"]))
    #             start_node = cursor.fetchone()
    #             if start_node:
    #                  start_node_id = start_node["id"]
    #             else:
    #                 cursor.execute('INSERT INTO nodes (lat, lon) VALUES (?, ?)', (start["lat"], start["lon"]))
    #                 start_node_id = cursor.lastrowid
    #                 conn.commit()   

    #             cursor.execute('SELECT id FROM nodes WHERE lat=? AND lon=?', (end["lat"], end["lon"]))
    #             end_node = cursor.fetchone()
    #             if end_node:
    #                 end_node_id = end_node["id"]
    #             else:
    #                 cursor.execute('INSERT INTO nodes (lat, lon) VALUES (?, ?)', (end["lat"], end["lon"]))  
    #                 end_node_id = cursor.lastrowid
    #                 conn.commit()

    #         graph = build_graph()
    #         path, _ = dijkstra(graph, start_node_id, end_node_id, routing_type="fastest")
            

    #         route_coordinates = build_route_geometry(path)

    #         print("Route coordinates:", route_coordinates)

    #         route_steps=get_route_steps(path)

    #         route_coordinates = [(step.start_location.lat, step.start_location.lon) for step in route_steps]

    #         route_coordinates.append((route_steps[-1].end_location.lat, route_steps[-1].end_location.lon))

    #         total_distance = sum(step.distance for step in route_steps)
    #         total_duration = sum(step.duration for step in route_steps)


    #         def update(dt):
    #             if hasattr(self, "route_layer") and self.route_layer:
    #                 self.map.remove_layer(self.route_layer)
    #             self.route_layer = RouteLineLayer(self.map, route_coordinates)
    #             self.map.add_layer(self.route_layer)
    #             self.route_layer.reposition()
    #             self.nav_label.text = f"Маршрут: {total_distance:.0f} м, примерно {int(total_duration / 60)} мин"
    #             self.nav_label.text = f"Маршрут: {route_coordinates}"

    #         Clock.schedule_once(update)
    #     threading.Thread(target=worker, daemon=True).start()

       
            
       

    # def display_route(self, route_data):
    #         app = App.get_running_app()
    #         summary = route_data.get("summary", {})
    #         print("Summary:", summary)

    #         distance = summary.get("distance_meters", 0) / 1000
    #         duration = summary.get("duration_seconds", 0) / 60
    #         latest = app.route_api.save_location()

    #         recent_count = 0

    #         if latest:
    #             recent_count = latest.get("recent_routes_count", 0)

    #         self.route_info.text = (
    #           f"Расстояние: {distance:.2f} км\n"
    #           f"Время: {duration:.1f} мин\n" 
    #           f"Шагов: {summary.get('steps_count', 0)}"
    #           f"Недавние маршруты: {recent_count}"
    #           f"[ref=clear][color=0000ff]Очистить историю[/color][/ref]"
    #         )
    
    # def on_ref_press(self, instance, ref):
    #     if ref == "clear":
    #         def clear_worker():
    #             result = app.route_api.clear_location_history()
    #             # Обновляем информацию после очистки
    #             Clock.schedule_once(lambda dt: self.display_route({"summary": {}}))
    #     threading.Thread(target=clear_worker, daemon=True).start()



    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def draw_route(self, route_coords):
        self.route_layer = RouteLineLayer(self.map, route_coords)
        self.map.add_layer(self.route_layer)


    def load_map_style(self, style_id=1):
        #Загрузить стиль карты из API
        app = App.get_running_app()

        def fetch_data():
            # Загружаем стиль карты
            map_style = app.api_client.get_style(1)

            # Загружаем навигационную сеть
            nav_nodes = app.nav_api.get_nodes()

            # Получаем последнюю локацию
            last_location = app.nav_api.get_latest_location()

           

            Clock.schedule_once(
                lambda dt: self.on_data_loaded(map_style, nav_nodes, last_location), 0
            )

        threading.Thread(target=fetch_data, daemon=True).start()

    def on_data_loaded(self, map_style, nav_nodes, last_location):
        
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
        self.map_display = MapScreen()
        root.add_widget(self.map_display)
        white_bar = WhiteBar()
        root.add_widget(white_bar)
        self.bind_white_bar_buttons(white_bar)
        self.add_widget(root)

    # def on_enter(self):
        #Вызывается при входе на экран
        # self.map_display.load_map_style()

    def bind_white_bar_buttons(self, white_bar):
        for child in white_bar.walk():
            if isinstance(child, Button):
                if child.background_normal == "bests.png":
                    child.bind(on_press=self.go_to_new_window)
                if child.background_normal == "navi.png":
                    def start_route(instance):
                        app = App.get_running_app()
                        app.selecting_route = True
                        app.selected_start = None
                        app.selected_end = None
                        app.sm.current = "route_window"

                child.bind(on_press=start_route)

    def go_to_new_window(self, instance):
        App.get_running_app().sm.current = 'Популярные маршруты'
        




class RouteWindow(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
            valign='top',
            markup=True
        )
        self.route_info.bind(size=self.route_info.setter('text_size'),on_ref_press=self.on_ref_press)
        self.layout.add_widget(self.route_info)

        float_layout = FloatLayout()

        self.btn_back = Button(
            background_normal="exit.png",
            background_down="exit.png",
            size_hint=(None, None),
            size=(60, 53),
            pos=(730, 550)
        )

        self.btn_go = Button(
            background_normal="go.png",
            background_down="go.png",
            size_hint=(None, None),
            size=(200, 50),
            pos=(500, 600)
        )

        self.btn_go.bind(on_press=self.build_route)
        self.btn_back.bind(
            on_press=lambda x: setattr(App.get_running_app().sm, 'current', 'Популярные маршруты')
        )

        float_layout.add_widget(self.btn_back)
        float_layout.add_widget(self.btn_go)

        self.layout.add_widget(float_layout)
        self.add_widget(self.layout)

   
    def build_route(self, instance):
        

        start = app.selected_start
        end = app.selected_end

       

        def distance(lat1, lon1, lat2, lon2):
            return (lat1 - lat2) ** 2 + (lon1 - lon2) ** 2

        
        app.nav_api.create_node(start["lat"], start["lon"])
        app.nav_api.create_node(end["lat"], end["lon"])

        
        nodes = app.nav_api.get_nodes()
        edges = app.nav_api.get_edges()


        nodes = nodes["data"]
        edges = edges["data"]

        node_map = {n["id"]: n for n in nodes}

        edge_nodes = set()
        for edge in edges:
            edge_nodes.add(edge["from_node"])
            edge_nodes.add(edge["to_node"])

        
        def find_nearest(lat, lon):
            best_node = None
            best_dist = float("inf")

            for node_id in edge_nodes:
                node = node_map.get(node_id)
                if not node:
                    continue

                d = distance(lat, lon, node["lat"], node["lon"])

                if d < best_dist:
                    best_dist = d
                    best_node = node

            return best_node

        start_node = find_nearest(start["lat"], start["lon"])
        end_node = find_nearest(end["lat"], end["lon"])


        return app.nav_api.calculate_route(start_lat=start_node["lat"],start_lon=start_node["lon"],
            end_lat=end_node["lat"],
            end_lon=end_node["lon"]
        )

    
    def on_touch_down(self, touch):
        if touch.is_double_tap:
            

            start = app.selected_start
            end = app.selected_end

            

            return app.nav_api.get_route_with_map(
                start_lat=start["lat"],
                start_lon=start["lon"],
                end_lat=end["lat"],
                end_lon=end["lon"]
            )


        return super().on_touch_down(touch)
    

    def double_touch(instance, touch):
        if not touch.is_double_tap:
            

            selected = app.selected_coords
            end = app.selected_end

            app.nav_api.create_node(selected["lat"], selected["lon"])
            app.nav_api.create_node(end["lat"], end["lon"])

            nodes = app.nav_api.get_nodes()
            edges = app.nav_api.get_edges()

    

            nodes = nodes["data"]
            edges = edges["data"]

    
            node_map = {n["id"]: n for n in nodes}

   
            edge_nodes = set()

            for edge in edges:
                edge_nodes.add(edge["from_node"])
                edge_nodes.add(edge["to_node"])

    
        def distance(lat1, lon1, lat2, lon2):
            return (lat1 - lat2) ** 2 + (lon1 - lon2) ** 2

  
        def find_nearest(lat, lon):
            best_node = None
            best_dist = float("inf")

            for node_id in edge_nodes:
                node = node_map.get(node_id)
                      
            d = distance(lat, lon, node["lat"], node["lon"])

            if d < best_dist:
                best_dist = d
                best_node = node

            return best_node

    
        
        end_node = find_nearest(end["lat"], end["lon"])

    
    
        return app.nav_api.calculate_route_from_current(
            end_lat=end_node["lat"],
            end_lon=end_node["lon"]
    )
    
    def load_route_data(self, route_id):
        app = App.get_running_app()

        routes_coords = {
            "Красная площадь": (55.7558, 37.6173, 55.7520, 37.6175),
            "Парк Сокольники": (55.7904, 37.6707, 55.7950, 37.6750),
        }

        if route_id not in routes_coords:
            return

        coords = routes_coords[route_id]

        def fetch():
            data = app.api_client.get_map_with_route(
                start_lat=coords[0],
                start_lon=coords[1],
                end_lat=coords[2],
                end_lon=coords[3],
                routing_type="fastest"
            )

            if data:
                Clock.schedule_once(lambda dt: self.display_route(data), 0)

        threading.Thread(target=fetch, daemon=True).start()


# Route Window

class RouteLineLayer(MapLayer):
    def __init__(self, mapview, route_points, **kwargs):
        super().__init__(**kwargs)
        self.mapview = mapview
        self.route_points = route_points

    def reposition(self):
        self.canvas.clear()

        if not self.route_points:
            return

        with self.canvas:
            Color(1, 0, 0, 1)  

            points = []
            for lat, lon in self.route_points:
                x, y = self.mapview.get_window_xy_from(lat, lon, self.mapview.zoom)
                points.extend([x, y])

            Line(points=points, width=3)




class RouteWindow(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation="vertical")

        self.map = MapView(
            lat=55.751244,
            lon=37.618423,
            zoom=12
        )

        layout.add_widget(self.map)

        btn_go = Button(
            background_normal="go.png",
            background_down="go.png",
            size_hint=(1, 0.1)
        )

        btn_go.bind(on_press=self.build_route)

        layout.add_widget(btn_go)

        self.add_widget(layout)

    def build_route(self, instance):

        app = App.get_running_app()

        start = app.selected_start
        end = app.selected_end

        def worker():

            nodes_response = app.nav_api.get_nodes()
            edges_response = app.nav_api.get_edges()

            nodes = nodes_response["data"]
            edges = edges_response["data"]

            node_map = {n["id"]: n for n in nodes}

            def distance(a, b, c, d):
                return (a - c) ** 2 + (b - d) ** 2

            def nearest(lat, lon):

                best_node = None
                best_dist = float("inf")

                for edge in edges:

                    for nid in (edge["from_node"], edge["to_node"]):

                        node = node_map.get(nid)

                        if not node:
                            continue

                        d = distance(
                            lat,
                            lon,
                            node["lat"],
                            node["lon"]
                        )

                        if d < best_dist:
                            best_dist = d
                            best_node = node

                return best_node

            start_node = nearest(
                start["lat"],
                start["lon"]
            )

            end_node = nearest(
                end["lat"],
                end["lon"]
            )

            if not start_node or not end_node:
                return

            route = app.nav_api.calculate_route(
                start_lat=start_node["lat"],
                start_lon=start_node["lon"],
                end_lat=end_node["lat"],
                end_lon=end_node["lon"]
            )

            if not route:
                return

            coords = route.get(
                "geometry",
                {}
            ).get(
                "coordinates",
                []
            )

            route_points = [
                (lat, lon)
                for lon, lat in coords
            ]

            def update_ui(dt):

                if not route_points:
                    return

                self.draw_route(route_points)

            Clock.schedule_once(update_ui)

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def draw_route(self, route_points):

        if hasattr(self, "route_layer"):

            try:
                self.map.remove_layer(
                    self.route_layer
                )
            except:
                pass

        self.route_layer = RouteLineLayer(
            self.map,
            route_points
        )

        self.map.add_layer(
            self.route_layer
        )

        self.route_layer.reposition()

    def double_touch(self, touch):

        if not touch.is_double_tap:
            return super().on_touch_down(touch)

        app = App.get_running_app()

        lat, lon = self.pixel_to_latlon(
            *touch.pos
        )

        nodes_response = app.nav_api.get_nodes()
        edges_response = app.nav_api.get_edges()

        nodes = nodes_response["data"]
        edges = edges_response["data"]

        node_map = {
            n["id"]: n
            for n in nodes
        }

        edge_nodes = set()

        for edge in edges:
            edge_nodes.add(edge["from_node"])
            edge_nodes.add(edge["to_node"])

        def distance(lat1, lon1, lat2, lon2):
            return (
                (lat1 - lat2) ** 2 +
                (lon1 - lon2) ** 2
            )

        def find_nearest(lat, lon):

            best_node = None
            best_dist = float("inf")

            for node_id in edge_nodes:

                node = node_map.get(node_id)

                if not node:
                    continue

                d = distance(
                    lat,
                    lon,
                    node["lat"],
                    node["lon"]
                )

                if d < best_dist:
                    best_dist = d
                    best_node = node

            return best_node

        end_node = find_nearest(
            lat,
            lon
        )

        if not end_node:
            return

        route = app.nav_api.calculate_route_from_current(
            end_lat=end_node["lat"],
            end_lon=end_node["lon"]
        )

        return route



   



class NewWindowScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
        content_layout.bind(minimum_height=content_layout.setter('height'))

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

        self.more= RoundedButton(
            text="Достопримечательности рядом",
            size_hint_y=None,
            width=100

        )

        

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
        import requests

        self.ext_search_mode = False
        self.selecting_route = False
        self.selected_start = None
        self.selected_end = None
        app.search_mode = False
        app.search_markers = []


        try:
            print("CHECK 8001")
            r = requests.get("http://localhost:8001/api/v1/health", timeout=3)
            print(r.text)
        except Exception as e:
            print("НЕ ДОСТУЧАЛСЯ:", e)

        try:
            print("CHECK 800")
            r = requests.get("http://localhost:8000/health", timeout=3)
            print(r.text)
        except Exception as e:  
            print("НЕ ДОСТУЧАЛСЯ too:", e)
        
        self.api_client = MapsAPIClient(base_url="http://localhost:8000")
        self.nav_api = NavigationAPIClient(base_url="http://localhost:8001")

        # Проверка подключения
        maps_ok = self.api_client.health_check() is not None
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
        self.sm.add_widget(RouteScreen(name='route_window'))
        return self.sm

    def on_stop(self):
        
        self.api_client.close()
        self.nav_api.close()

if __name__ == '__main__':
    MyApp().run()  


















