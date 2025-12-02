import flet as ft
from ui.dashboard import Dashboard
from ui.login import LoginView
from services.auth_service import GoogleAuth

def main(page: ft.Page):
    page.window_always_on_top = True

    page.title = "Google Drive Folder Manager"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.window_width = 1200
    page.window_height = 800
    page.window_min_width = 800
    page.window_min_height = 600
    
    # Initialize auth service
    auth = GoogleAuth()
    
    def show_dashboard():
        """Switch to dashboard view"""
        page.controls.clear()
        dashboard = Dashboard(page, auth, show_login)
        page.add(dashboard.get_view())   # <-- FIXED
        page.update()
    
    def show_login():
        """Switch to login view"""
        page.controls.clear()
        login = LoginView(page, auth, show_dashboard)
        page.add(login)  # LoginView IS a control, so this is OK
        page.update()
    
    # Check if already authenticated
    if auth.is_authenticated():
        show_dashboard()
    else:
        show_login()

if __name__ == "__main__":
    ft.app(target=main)
