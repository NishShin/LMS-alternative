import flet as ft
from flet import Icon, Icons, Text, FontWeight, TextAlign, Container, ElevatedButton, Colors


class LoginView(ft.Column):
    def __init__(self, page, provider, auth_service, on_success=None):
        super().__init__(
            controls=[
                Container(height=50),
                Icon(Icons.CLOUD_CIRCLE, size=100, color=Colors.BLUE),
                Container(height=20),
                Text(
                    "Learning Management System",
                    size=32,
                    weight=FontWeight.BOLD,
                    text_align=TextAlign.CENTER
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True
        )

        self.page = page
        self.provider = provider
        self.auth = auth_service
        self.on_success = on_success
        
        self.status_text = Text("Please log in to continue", color=Colors.GREY)
        self.controls.append(self.status_text)

        self.login_button = ElevatedButton(
            text="Login with Google",
            icon=Icons.LOGIN,
            on_click=self.handle_login,
            style=ft.ButtonStyle(
                bgcolor=Colors.BLUE,
                color=Colors.WHITE,
                padding=ft.Padding(10, 5, 10, 5),
            )
        )
        self.controls.append(self.login_button)

    def handle_login(self, e):
        platform = self.page.platform
        print(f"Login initiated on platform: {platform}")

        if platform in [ft.PagePlatform.WINDOWS, ft.PagePlatform.LINUX, ft.PagePlatform.MACOS]:
            self.status_text.value = "Opening browser for Desktop Login..."
            self.status_text.color = Colors.BLUE
            self.page.update()
            
            try:
                self.auth.login_desktop()
                if self.auth.is_authenticated():
                     self.status_text.value = "Desktop Login Successful!"
                     self.status_text.color = Colors.GREEN
                     self.page.update()
                     if self.on_success:
                         self.on_success()
            except Exception as ex:
                self.status_text.value = f"Desktop Login Failed: {ex}"
                self.status_text.color = Colors.RED
                self.page.update()
                print(f"Desktop login error: {ex}")

        else:
            self.status_text.value = "Redirecting to Google (Mobile/Web)..."
            self.status_text.color = Colors.BLUE
            self.page.update()
            try:
                self.page.login(self.provider)
            except Exception as e:
                self.status_text.value = f"Mobile Login Error: {e}"
                self.status_text.color = Colors.RED
                self.page.update()
