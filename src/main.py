import os
import sys
import time
import json
import flet as ft

def main(page: ft.Page):
    page.title = "System Check"
    page.bgcolor = ft.Colors.BLACK
    
    log_column = ft.Column()
    page.add(
        ft.Container(
            content=log_column,
            padding=20,
        )
    )
    
    def log(msg, color=ft.Colors.GREEN):
        log_column.controls.append(ft.Text(msg, color=color, size=16, font_family="monospace"))
        page.update()
        print(msg) 

    log("1. Application Started", ft.Colors.CYAN)
    
    try:
        
        log("2. Checking sys.path...")
        if os.getcwd() not in sys.path:
            sys.path.append(os.getcwd())
        log("   sys.path OK")

        log("3. Running Filesystem Repair...")
        try:
            cwd = os.getcwd()
            files = os.listdir(cwd)
            fixed_any = False
            for filename in files:
                if "\\" in filename:
                    new_path = filename.replace("\\", os.sep)
                    dir_name = os.path.dirname(new_path)
                    if dir_name and not os.path.exists(dir_name):
                        os.makedirs(dir_name, exist_ok=True)
                    try:
                        os.rename(filename, new_path)
                        fixed_any = True
                    except OSError:
                        pass
            if fixed_any:
                log("   Repaired files.", ft.Colors.YELLOW)
            else:
                log("   No repairs needed.")
        except Exception as e:
            log(f"   Repair Warning: {e}", ft.Colors.ORANGE)

        log("4. Importing Modules...", ft.Colors.CYAN)
        
        log("   Importing flet.auth...")
        from flet.auth.providers import GoogleOAuthProvider
        log("   ...OK")
        
        log("   Importing google.oauth2...")
        from google.oauth2.credentials import Credentials
        log("   ...OK")
        
        log("   Importing auth_service...")
        from services.auth_service import GoogleAuth
        log("   ...OK")

        log("   Importing UI...")
        from ui.dashboard import Dashboard
        from ui.login import LoginView
        log("   ...OK")

        log("5. Initializing Services...", ft.Colors.CYAN)
        auth_service = GoogleAuth()
        log("   Auth Service Init OK")
        log("6. Loading Credentials...", ft.Colors.CYAN)
        client_id = None
        client_secret = None
        
        creds_path = os.path.join(os.path.dirname(__file__), "credentials.json") 
        if not os.path.exists(creds_path):
             creds_path = os.path.join(os.path.dirname(__file__), "services", "credentials.json")
        
        if os.path.exists(creds_path):
             log(f"   Found file at: {creds_path}")
             with open(creds_path, 'r') as f:
                 data = json.load(f)
                 config = data.get('installed') or data.get('web')
                 if config:
                     client_id = config.get('client_id')
                     client_secret = config.get('client_secret')
                     log("   Credentials parsed OK")
                 else:
                     log("   ERROR: Invalid JSON structure", ft.Colors.RED)
        else:
             log(f"   ERROR: File not found. Checked: {creds_path}", ft.Colors.RED)

        log("7. Launching UI...", ft.Colors.CYAN)
        time.sleep(1) 
        
        page.clean()
        page.title = "LMS Alternative"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = ft.Colors.WHITE
        page.padding = 0

        if client_id and client_secret:
            provider = GoogleOAuthProvider(
                client_id=client_id,
                client_secret=client_secret,
                redirect_url="http://localhost:8550/oauth_callback"
            )
            provider.scopes = ["https://www.googleapis.com/auth/drive"]
            
            def show_dashboard():
                page.clean()
                dashboard = Dashboard(page, auth_service, handle_logout)
                if hasattr(dashboard, 'get_view'):
                    page.add(dashboard.get_view())
                else:
                    page.add(dashboard)
                page.update()

            def handle_logout():
                auth_service.logout()
                page.auth.logout()
                show_login()

            def show_login():
                page.clean()
                page.add(LoginView(page, provider, auth_service, on_success=show_dashboard))
                page.update()

            def on_login_success(e):
                if e.error:
                    log(f"Login Error: {e.error}", ft.Colors.RED)
                    return
                token = page.auth.token
                creds = Credentials(
                    token=token.access_token,
                    refresh_token=token.refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=provider.scopes
                )
                auth_service.set_credentials(creds)
                show_dashboard()

            page.on_login = on_login_success
            
            if auth_service.is_authenticated():
                 show_dashboard()
            else:
                 show_login()
        else:
            page.add(ft.Text("CRITICAL: Missing Credentials. See log.", color="red", size=20))
            
    except Exception as e:
        log(f"CRITICAL ERROR: {e}", ft.Colors.RED)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    ft.app(target=main)