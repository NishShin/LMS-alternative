import flet as ft

class LoginView(ft.Control):
    """Login screen for Google Drive authentication"""
    
    def __init__(self, page, auth_service, on_success):
        super().__init__()
        self.page = page
        self.auth = auth_service
        self.on_success = on_success
        self.status_text = ft.Text("", color=ft.Colors.RED, size=14)
        self.login_button = ft.ElevatedButton(
            "Login with Google",
            icon=ft.Icons.LOGIN,
            on_click=self.handle_login,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE,
                padding=20
            )
        )
    
    def handle_login(self, e):
        """Handle login button click"""
        self.login_button.disabled = True
        self.status_text.value = "Opening browser for authentication..."
        self.status_text.color = ft.Colors.BLUE
        self.update()
        
        success, message = self.auth.login()
        
        if success:
            self.status_text.value = message
            self.status_text.color = ft.Colors.GREEN
            self.update()
            # Wait a moment then switch to dashboard
            self.page.run_task(self.delayed_success)
        else:
            self.status_text.value = message
            self.status_text.color = ft.Colors.RED
            self.login_button.disabled = False
            self.update()
    
    async def delayed_success(self):
        """Wait 1 second then show dashboard"""
        import asyncio
        await asyncio.sleep(1)
        self.on_success()
    
    def build(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=50),
                    ft.Icon(
                        ft.Icons.CLOUD_CIRCLE,
                        size=100,
                        color=ft.Colors.BLUE
                    ),
                    ft.Container(height=20),
                    ft.Text(
                        "Google Drive Folder Manager",
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Text(
                        "Manage multiple folders with ease",
                        size=16,
                        color=ft.Colors.GREY_700,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=40),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Setup Instructions:",
                                    size=16,
                                    weight=ft.FontWeight.BOLD
                                ),
                                ft.Text("1. Go to Google Cloud Console"),
                                ft.Text("2. Create a new project"),
                                ft.Text("3. Enable Google Drive API"),
                                ft.Text("4. Create OAuth 2.0 credentials"),
                                ft.Text("5. Download credentials.json"),
                                ft.Text("6. Place it in the project root folder"),
                            ],
                            spacing=5
                        ),
                        padding=20,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=10,
                        width=400
                    ),
                    ft.Container(height=30),
                    self.login_button,
                    ft.Container(height=10),
                    self.status_text
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            expand=True,
            alignment=ft.alignment.center
        )