#! /usr/bin/env python3

import kivy
kivy.require('1.10.0')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.core.window import Window
Window.size = (350, 600)

Builder.load_string("""
#:import Factory kivy.factory.Factory
#:import QRCodeWidget kivy.garden.qrcode
# import ZbarQrcodeDetector android-zbar-qrcode.main

<SendScreen>:
    BoxLayout:
        orientation: "vertical"
        spacing: 3
        ActionBar:
            pos_hint: {'top':1}
            ActionView:
                use_separator: True
                ActionPrevious:
                    app_icon: "icons/brain.png"
                    title: "NOWALLET"
                    with_previous: False
                ActionOverflow:
        BoxLayout:
            size_hint: 1, 0.15
            TextInput:
                background_color: (0.7, 0.7, 0.7, 1)
                padding_y: ( self.height - self.line_height ) / 2
            Label:
                text: "BTC / USD"
            TextInput:
                background_color: (0.7, 0.7, 0.7, 1)
                padding_y: ( self.height - self.line_height ) / 2
        Label:
            size_hint: 1, 0.2
            text: "Available balance: 1.20049387 BTC"
        BoxLayout:
            size_hint: 1, 0.15
            TextInput:
                hint_text: "Enter Address:"
                hint_text_color: (0.9, 0.9, 0.9, 1)
                background_color: (0.7, 0.7, 0.7, 1)
                padding_y: ( self.height - self.line_height ) / 2
            Button:
                size_hint_x: 0.2
                Image:
                    source: 'icons/qr.png'
                    y: self.parent.y + 3
                    x: self.parent.x + 3
                    width: self.parent.width - 6
                    height: self.parent.height - 6
        BoxLayout:
            size_hint: 1, 0.15
            TextInput:
                hint_text: "Fee: 50 sat/byte"
                hint_text_color: (0.9, 0.9, 0.9, 1)
                background_color: (0.7, 0.7, 0.7, 1)
                padding_y: ( self.height - self.line_height ) / 2
            ToggleButton:
                size_hint: 0.5, 1
                text: "Custom Fee"
            ToggleButton:
                size_hint: 0.5, 1
                text: "Use RBF"
#        ZbarQrcodeDetector:
        Label:
            text: ""
        Button:
            text: "Back"
            size_hint: 1, 0.23
            on_press: root.manager.current = "main"

<RecieveScreen>:
    BoxLayout:
        spacing: 3
        orientation: "vertical"
        ActionBar:
            pos_hint: {'top':1}
            ActionView:
                use_separator: True
                ActionPrevious:
                    app_icon: "icons/brain.png"
                    title: "NOWALLET"
                    with_previous: False
                ActionOverflow:
        BoxLayout:
            size_hint: 1, 0.15
            TextInput:
                background_color: (0.7, 0.7, 0.7, 1)
                padding_y: ( self.height - self.line_height ) / 2
            Label:
                text: "BTC / USD"
            TextInput:
                background_color: (0.7, 0.7, 0.7, 1)
                padding_y: ( self.height - self.line_height ) / 2
        AnchorLayout:
            QRCodeWidget:
                size_hint: 0.8, 0.8
                show_border: False
                data: "bitcoin://129834hg2uin20eifvnjf0eifcmvdkv2d"
        Label:
            size_hint: 1, 0.3
            text: "Address: 129834hg2uin20eifvnjf0eifcmvdkv2d"
        Button:
            size_hint: 1, 0.2
            text: "Back"
            on_press: root.manager.current = "main"

<WaitScreen>:
    AnchorLayout:
        Image:
            source: "icons/throbber.gif"
            size_hint: 0.2, 0.2
    BoxLayout:
        orientation: "vertical"
        Label:
            font_size: "23sp"
            text: "Loading..."
        Label:

<XPUBScreen>:
    BoxLayout:
        orientation: "vertical"
        Label:
            font_size: "23sp"
            size_hint: 1, 0.2
            text: "Your eXtended PUBlic key:"
        AnchorLayout:
            QRCodeWidget:
                size_hint: 0.8, 0.65
                show_border: False
                data: "xpub039jf20fj01ijf38fj429hf3i4fb29yehf2748fh4ghg98jfi0j204f"
        Button:
            size_hint: 1, 0.15
            text: "Back"
            on_press: root.manager.current = "main"

<MyPopup@Popup>:
    title: "Menu"
    auto_dismiss: False
    BoxLayout:
        orientation: "vertical"
        Button:
            text: "View XPUB"
            size_hint: 1, 0.2
            on_release: app.sm.current = "xpub"
            on_release: root.dismiss()
        Button:
            text: "Send coins"
            size_hint: 1, 0.2
            on_release: app.sm.current = "send"
            on_release: root.dismiss()
        Button:
            text: "Recieve coins"
            size_hint: 1, 0.2
            on_release: app.sm.current = "recieve"
            on_release: root.dismiss()
        Button:
            text: "Close"
            size_hint: 1, 0.2
            on_release: root.dismiss()
        Label:

<MainScreen>:
    BoxLayout:
        orientation: "vertical"
        ActionBar:
            pos_hint: {'top':1}
            ActionView:
                use_separator: True
                ActionPrevious:
                    app_icon: "icons/brain.png"
                    title: "NOWALLET"
                    with_previous: False
                ActionButton:
                    on_release: Factory.MyPopup().open()
                    Image:
                        source: 'icons/settings.png'
                        y: self.parent.y + 5
                        x: self.parent.x + 5
                        width: self.parent.width - 10
                        height: self.parent.height - 10
                ActionOverflow:
        Label:
            size_hint: 1, 0.3
            font_size: "30sp"
            text: "1.20049387 BTC"
        ScrollView:
            do_scroll_x: False
            GridLayout:
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                Button:
                    size_hint_y: None
                    height: 50
                    text: "Recieved 0.5 BTC"
                Button:
                    size_hint_y: None
                    height: 50
                    text: "Recieved 1 BTC"
                Button:
                    size_hint_y: None
                    height: 50
                    text: "Sent 0.299 BTC"
        BoxLayout:
            size_hint: 1, 0.18
            Button:
                font_size: "30sp"
                text: "Recieve"
                on_press: root.manager.current = "recieve"
            Button:
                font_size: "30sp"
                text: "Send"
                on_press: root.manager.current = "send"

<LoginScreen>:
    ActionBar:
        pos_hint: {'top':1}
        ActionView:
            use_separator: True
            ActionPrevious:
                app_icon: "icons/brain.png"
                title: "NOWALLET"
                with_previous: False
            ActionOverflow:
    AnchorLayout:
        BoxLayout:
            size_hint: 0.8, 0.5
            spacing: 3
            orientation: "vertical"
            Label:
                text: "Email/Salt"
            TextInput:
                write_tab: False
                hint_text: "email@domain.tld"
                hint_text_color: (0.9, 0.9, 0.9, 1)
                background_color: (0.7, 0.7, 0.7, 1)
                padding_y: ( self.height - self.line_height ) / 2
            Label:
                text: "Passphrase"
            TextInput:
                password: True
                write_tab: False
                background_color: (0.7, 0.7, 0.7, 1)
                padding_y: ( self.height - self.line_height ) / 2
            Label:
                text: "Confirm Passphrase"
            TextInput:
                password: True
                write_tab: False
                background_color: (0.7, 0.7, 0.7, 1)
                padding_y: ( self.height - self.line_height ) / 2
            Button:
                text: "Create Wallet"
                on_press: root.manager.current = "main"
""")

# Declare screens
class LoginScreen(Screen):
    pass

class MainScreen(Screen):
    pass

class RecieveScreen(Screen):
    pass

class SendScreen(Screen):
    pass

class WaitScreen(Screen):
    pass

class XPUBScreen(Screen):
    pass

# Create the screen manager
transition = SlideTransition(direction="up")
sm = ScreenManager(transition=transition)
sm.add_widget(LoginScreen(name="login"))
sm.add_widget(MainScreen(name="main"))
sm.add_widget(RecieveScreen(name="recieve"))
sm.add_widget(SendScreen(name="send"))
sm.add_widget(WaitScreen(name="wait"))
sm.add_widget(XPUBScreen(name="xpub"))

class NowalletApp(App):
    def __init__(self):
        self.sm = sm
        super().__init__()

    def build(self):
        return self.sm

if __name__ == "__main__":
    NowalletApp().run()
