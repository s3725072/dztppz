from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle,Line
from kivy.core.image import Image as CoreImage


class SearchBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.size_hint = (None, None)
        self.size = (300, 50)
        self.padding = [6, 6]   
        self.orientation = 'horizontal'

        with self.canvas.before:
            
            Color(0.75, 0.75, 0.75, 1)
            self.border = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[15]
            )

            Color(1, 1, 1, 1)
            self.bg = RoundedRectangle(
                pos=(self.x + 3, self.y + 3),
                size=(self.width - 4, self.height - 6),
                radius=[13]
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
            padding=[10, 10, 10, 10],   
        )

        self.add_widget(self.search_input)

    def update_bg(self, *args):
        self.border.pos = self.pos
        self.border.size = self.size
        self.bg.pos = (self.x + 2, self.y + 2)
        self.bg.size = (self.width - 2, self.height - 4)


# class RoundedButton(Button):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.background_normal = ''  # Remove default background
#         self.background_color = (1, 1, 1, 1)  
#         self.color = kwargs.get('color', (0, 0, 0, 1))
#         self.font_size = kwargs.get('font_size', 12)

#         with self.canvas.before:
#             Color(*kwargs.get('bg_color', (1, 1, 1, 1)))  # Background color
#             self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[15])

#         self.bind(pos=self.update_bg, size=self.update_bg)

#     def update_bg(self, *args):
#         self.bg.pos = self.pos
#         self.bg.size = self.size


class WhiteBar(AnchorLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.orientation = 'horizontal'
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
                rounded_rectangle=(btn1.x, btn1.y, btn1.width, btn1.height,10),
                width=0.5  
            )


        def update_border1(instance, value):
            instance.border_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height,10)

        btn1.bind(pos=update_border1, size=update_border1)

        btn2=Button(background_normal="bests.png", background_down="bests.png", size_hint=(None,None), size=(56,43), border=(1,1,1,1), background_color=(1,1,1,1), color=(0,0,0,1))   

        with btn2.canvas.after:
           Color(0,0,0,1)
           btn2.border_line=Line(
                rounded_rectangle=(btn2.x, btn2.y, btn2.width, btn2.height, 10),
                width=0.5
           )
        
        def update_border2(instance,value):
            instance.border_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 10)

        btn2.bind(pos=update_border2, size=update_border2)

        button_container.add_widget(btn1)
        button_container.add_widget(btn2)
        center_anchor.add_widget(button_container)
        self.add_widget(center_anchor)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


class MyApp(App):
    def build(self):
        root = BoxLayout(orientation='vertical', padding=10)

        top_bar = AnchorLayout(
            anchor_x='center',
            anchor_y='top',
        )

       
        top_bar.add_widget(SearchBar())

        root.add_widget(top_bar) 
        
        root.add_widget(WhiteBar())
        return root


if __name__ == '__main__':
    MyApp().run()

