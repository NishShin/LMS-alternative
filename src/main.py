import os
import sys
import json
import flet as ft


def setup_paths():
    app_path = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    
    for path in [cwd, app_path]:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    return app_path, cwd


def repair_filesystem(cwd):
    try:
        files = os.listdir(cwd)
        for filename in files:
            if "\\" in filename:
                new_path = filename.replace("\\", os.sep)
                dir_name = os.path.dirname(new_path)
                if dir_name and not os.path.exists(dir_name):
                    os.makedirs(dir_name, exist_ok=True)
                try:
                    os.rename(filename, new_path)
                except OSError:
                    pass
    except Exception:
        pass


def load_credentials(app_path, cwd):
    possible_paths = [
        os.path.join(app_path, "services", "web.json"),
        os.path.join(cwd, "services", "web.json"),
        os.path.join(app_path, "web.json"),
        os.path.join(cwd, "web.json")
    ]
    
    for creds_path in possible_paths:
        if os.path.exists(creds_path):
            try:
                with open(creds_path, 'r') as f:
                    data = json.load(f)
                    config = data.get('web') or data.get('installed')
                    
                    if not config:
                        continue
                    
                    return {
                        'path': creds_path,
                        'client_id': config.get('client_id'),
                        'client_secret': config.get('client_secret'),
                        'redirect_uris': config.get('redirect_uris', [])
                    }
            except Exception:
                continue
    
    return None


def get_redirect_url():
    return "http://localhost:8550/oauth_callback"


def main(page: ft.Page):
    page.title = "LMS Alternative"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.WHITE
    page.padding = 0
    
    try:
        app_path, cwd = setup_paths()
        repair_filesystem(cwd)
        
        from services.auth_service import GoogleAuth
        from ui.dashboard import Dashboard
        from ui.login import LoginView
        
        try:
            from ui.firebase_mobile_login import FirebaseMobileLogin
        except ImportError:
            FirebaseMobileLogin = None
        
        creds = load_credentials(app_path, cwd)
        if not creds:
            page.add(ft.Text("ERROR: web.json not found!", color=ft.Colors.RED))
            page.update()
            return

        redirect_url = get_redirect_url()
        auth_service = GoogleAuth(credentials_file=creds['path'])
        
        from flet.auth.providers import GoogleOAuthProvider
        
        provider = GoogleOAuthProvider(
            client_id=creds['client_id'],
            client_secret=creds['client_secret'],
            redirect_url=redirect_url
        )
        provider.scopes = ["openid", "email", "profile"]
        
        def handle_on_login(e):
            if e.error:
                show_snackbar(f"Login Error: {e.error}")
                return
            
            if not hasattr(page.auth, 'token') or not page.auth.token:
                show_snackbar("Authentication failed: No token received")
                return
            
            token_data = page.auth.token
            
            if isinstance(token_data, dict):
                token_data['client_id'] = creds['client_id']
                token_data['client_secret'] = creds['client_secret']
            
            if auth_service.login_with_token(token_data):
                show_dashboard()
            else:
                show_snackbar("Authentication failed: Could not complete login")
        
        page.on_login = handle_on_login
        
        def show_snackbar(message):
            page.snack_bar = ft.SnackBar(content=ft.Text(message), action="Dismiss")
            page.snack_bar.open = True
            page.update()
        
        def show_dashboard():
            page.controls.clear()
            dashboard = Dashboard(page, auth_service, handle_logout)
            page.add(dashboard.get_view() if hasattr(dashboard, 'get_view') else dashboard)
            page.update()
        
        def handle_logout():
            auth_service.logout()
            if hasattr(page.auth, 'logout'):
                page.auth.logout()
            show_login()
        
        def show_login():
            page.controls.clear()
            
            is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
            
            if is_mobile and FirebaseMobileLogin:
                firebase_config_path = os.path.join(app_path, "services", "firebase_config.json")
                if not os.path.exists(firebase_config_path):
                    firebase_config_path = os.path.join(cwd, "services", "firebase_config.json")
                
                firebase_config = {}
                if os.path.exists(firebase_config_path):
                    with open(firebase_config_path, 'r') as f:
                        firebase_config = json.load(f)
                
                page.add(FirebaseMobileLogin(
                    page, 
                    auth_service, 
                    firebase_config,
                    creds['client_id'],
                    on_success=show_dashboard
                ))
            else:
                page.add(LoginView(page, provider, auth_service, on_success=show_dashboard))
            
            page.update()
        
        if auth_service.is_authenticated():
            show_dashboard()
        else:
            show_login()
            
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        page.add(ft.Text(f"CRITICAL ERROR: {e}", color=ft.Colors.RED))
        page.update()
        print(f"CRITICAL ERROR:\n{error_msg}")


if __name__ == "__main__":
    ft.app(target=main)