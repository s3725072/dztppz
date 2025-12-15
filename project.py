from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle,Line,Rectangle
from kivy.core.image import Image as KivyImage
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout

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


class WhiteBar(AnchorLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
            border=(1,1,1,1),
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
            border=(1,1,1,1),
            background_color=(1,1,1,1),
            color=(0,0,0,1)
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





class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = BoxLayout(orientation='vertical')

        # Top Search Bar
        top_bar = AnchorLayout(
            anchor_x='center',
            anchor_y='top',
            height=100
        )

        
        top_bar.add_widget(SearchBar())
        root.add_widget(top_bar)

        # Bottom White Bar
        white_bar = WhiteBar()
        root.add_widget(white_bar)

        # Bind buttons inside WhiteBar
        self.bind_white_bar_buttons(white_bar)

        self.add_widget(root)

    def bind_white_bar_buttons(self, white_bar):
        for child in white_bar.walk():
            if isinstance(child, Button):
                child.bind(on_press=self.go_to_new_window)

    def go_to_new_window(self, instance):
        App.get_running_app().sm.current = 'Популярные маршруты'


class RoundedButton(Button):
    def __init__(self, **kwargs):
        
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        kwargs.setdefault('color', (0, 0, 0, 1))
          
        super().__init__(**kwargs)

        
        with self.canvas.after:
            Color(0, 0, 0, 1)  
            self.border_line = Line(rounded_rectangle=(self.x,self.y,self.width,self.height,10),width=0.5)
        

        
        self.bind(pos=self.update_border, size=self.update_border)

    def update_bg(self, instance, value):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def update_border(self,instance,value):
        instance.border_line.rounded_rectangle=(instance.x, instance.y, instance.width, instance.height,10)


from kivy.uix.widget import Widget


class RouteWindow(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20)
        
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)


        self.title_label = Label(
            text="Загрузка...",
            font_size=14,
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=50
        )
        self.layout.add_widget(self.title_label)
        
        btn_back = Button(
            text="Назад",
            size_hint_y=None,
            height=50,
            on_press=self.go_back
        )

        self.layout.add_widget(btn_back)
        
        self.add_widget(self.layout)

    def set_route(self, route_id):
        
        self.title_label.text = f"Информация о Маршруте {route_id}"

    def go_back(self, instance):
        App.get_running_app().sm.current = 'Популярные маршруты'

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size 


class NewWindowScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        
        main_layout = BoxLayout(orientation='vertical', padding=[10, 10], spacing=10)

        
        top_bar = BoxLayout(size_hint_y=None, height=50)

        
        btn_back = Button(
            background_normal="exit.png",
            background_down="exit.png",
            size_hint=(None, 1),
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
            bold=True
        )

        top_bar.add_widget(btn_back)
        top_bar.add_widget(title_label)
        main_layout.add_widget(top_bar)

        content_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        content_layout.bind(minimum_height=content_layout.setter('height'))

        for i in range(5):
            route_id = i + 1
            item = RoundedButton(
                text=f"Маршрут {route_id}",
                size_hint_y=None,
                height=100,
            )
    
    
            def on_route_press(instance, rid=route_id):  
                app = App.get_running_app()
                route_screen = app.sm.get_screen('route_window')
                route_screen.set_route(rid)  
                app.sm.current = 'route_window'

            item.bind(on_press=on_route_press)
            content_layout.add_widget(item)

        
        scroll_view = ScrollView(size_hint=(1, 1),bar_color=(0.6, 0.6, 0.6, 1),bar_inactive_color=(0.8, 0.8, 0.8, 0.8))
        scroll_view.add_widget(content_layout)

        main_layout.add_widget(scroll_view)
        self.add_widget(main_layout)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
 

class MyApp(App):
    def build(self):
        self.sm = ScreenManager()
        self.sm.add_widget(MainScreen(name='Карта'))
        self.sm.add_widget(NewWindowScreen(name='Популярные маршруты'))
        self.sm.add_widget(RouteWindow(name='route_window')) 
        return self.sm


if __name__ == '__main__':
    MyApp().run()


# class NewWindowScreen(Screen):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)

#         with self.canvas.before:
#             Color(1, 1, 1, 1)
#             self.bg = Rectangle(pos=self.pos, size=self.size)
#         self.bind(pos=self.update_bg, size=self.update_bg)

        
#         main_layout = BoxLayout(orientation='vertical', padding=[10, 10], spacing=10)

        
#         top_bar = BoxLayout(size_hint_y=None, height=50)

        
#         btn_back = Button(
#             background_normal="exit.png",
#             background_down="exit.png",
#             size_hint=(None, 1),
#             width=60,
#             background_color=(1, 1, 1, 1),
#             color=(0, 0, 0, 1),
#             pos_hint={'x':0, 'top':1}
#         )

#         btn_back.bind(
#             on_press=lambda x: setattr(App.get_running_app().sm, 'current', 'Карта')
#         )

        
#         title_label = Label(
#             text="Популярные направления",
#             color=(0, 0, 0, 1),
#             font_size=20,
#             bold=True
#         )

#         top_bar.add_widget(btn_back)
#         top_bar.add_widget(title_label)
#         main_layout.add_widget(top_bar)

#         content_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
#         content_layout.bind(minimum_height=content_layout.setter('height'))

        

#         for i in range(5):
#             route_id=i+1
#             item = RoundedButton(
#                 text=f"Маршрут {route_id}",
#                 size_hint_y=None,
#                 height=100,
#             )
    
#         item.bind(on_press=lambda instance, rid=route_id: self.open_route(rid))

#         content_layout.add_widget(item)
    

#         def on_route_press(instance, rid=route_id):  
#             app = App.get_running_app()
#             route_screen = app.sm.get_screen('route_window')
#             route_screen.set_route(rid)  
#             app.sm.current = 'route_window'


#         scroll_view = ScrollView(size_hint=(1, 1),bar_color=(0.6, 0.6, 0.6, 1),bar_inactive_color=(0.8, 0.8, 0.8, 0.8))
#         scroll_view.add_widget(content_layout)

#         main_layout.add_widget(scroll_view)
#         self.add_widget(main_layout)

#     def update_bg(self, *args):
#         self.bg.pos = self.pos
#         self.bg.size = self.size












# class RouteWindow(Screen):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)

#         # White background
#         with self.canvas.before:
#             Color(1, 1, 1, 1)
#             self.bg = Rectangle(pos=self.pos, size=self.size)
#         self.bind(pos=self.update_bg, size=self.update_bg)

#         # Main layout: vertical
#         main_layout = BoxLayout(orientation='vertical', padding=[10, 10], spacing=10)

#         # === Header area (top-aligned) ===
#         header = BoxLayout(size_hint_y=None, height=60)
        
#         # Back button on the left
#         btn_back = Button(
#             background_normal="exit.png",
#             background_down="exit.png",
#             size_hint=(None, 1),
#             width=50,
#             background_color=(1, 1, 1, 1)
#         )
#         btn_back.bind(on_press=self.go_back)
#         header.add_widget(btn_back)

#         # Title centered in header
#         self.title_label = Label(
#             text="Загрузка...",
#             font_size=20,
#             color=(0, 0, 0, 1),
#             bold=True,
#             halign='center'
#         )
#         header.add_widget(self.title_label)

#         # Add empty widget to balance layout (optional)
#         header.add_widget(Widget(size_hint_x=None, width=50))

#         main_layout.add_widget(header)

#         # === Content area (scrollable if needed) ===
#         # For now, just an empty space or placeholder
#         content = Label(
#             text="Описание маршрута, карта, остановки и т.д.",
#             color=(0.3, 0.3, 0.3, 1),
#             size_hint_y=1,
#             halign='center',
#             valign='top'
#         )
#         content.bind(texture_size=content.setter('size'))
#         main_layout.add_widget(content)

#         self.add_widget(main_layout)

#     def set_route(self, route_id):
#         self.title_label.text = f"Информация о Маршруте {route_id}"

#     def go_back(self, instance):
#         App.get_running_app().sm.current = 'Популярные маршруты'

#     def update_bg(self, *args):
#         self.bg.pos = self.pos
#         self.bg.size = self.size





# class RouteWindow(Screen):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.layout = BoxLayout(orientation='vertical', padding=20)
        
#         with self.canvas.before:
#             Color(1, 1, 1, 1)
#             self.bg = Rectangle(pos=self.pos, size=self.size)
#         self.bind(pos=self.update_bg, size=self.update_bg)


#         self.title_label = Label(
#             text="Загрузка...",
#             font_size=14,
#             color=(0, 0, 0, 1),
#             size_hint_y=None,
#             height=50
#         )
#         self.layout.add_widget(self.title_label)
        
#         btn_back = Button(
#             text="Назад",
#             size_hint_y=None,
#             height=50,
#             on_press=self.go_back
#         )

#         self.layout.add_widget(btn_back)
        
#         self.add_widget(self.layout)

#     def set_route(self, route_id):
        
#         self.title_label.text = f"Информация о Маршруте {route_id}"

#     def go_back(self, instance):
#         App.get_running_app().sm.current = 'Популярные маршруты'

#     def update_bg(self, *args):
#         self.bg.pos = self.pos
#         self.bg.size = self.size






