import os
import sys
import json
import time
import flet as ft

def main(page: ft.Page):
    page.title = "System Check"
    page.bgcolor = ft.Colors.BLACK
    page.padding = 20
    
    log_column = ft.Column(scroll=ft.ScrollMode.AUTO)
    page.add(ft.Container(content=log_column, expand=True))
    
    def log(msg, color=ft.Colors.GREEN):
        log_column.controls.append(ft.Text(msg, color=color, size=14, font_family="monospace"))
        page.update()
        print(msg)

    log("1. Application Started", ft.Colors.CYAN)
    
    try:
        log("2. Checking sys.path...")
        app_path = os.path.dirname(os.path.abspath(__file__))
        cwd = os.getcwd()
        
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
            log(f"   Added CWD: {cwd}", ft.Colors.GREEN)
        if app_path not in sys.path:
            sys.path.insert(0, app_path)
            log(f"   Added app_path: {app_path}", ft.Colors.GREEN)
        
        log(f"   sys.path has {len(sys.path)} entries")

        log("3. Running Filesystem Repair...", ft.Colors.CYAN)
        try:
            files = os.listdir(cwd)
            fixed_any = False
            for filename in files:
                if "\\" in filename:
                    new_path = filename.replace("\\", os.sep)
                    dir_name = os.path.dirname(new_path)
                    if dir_name and not os.path.exists(dir_name):
                        os.makedirs(dir_name, exist_ok=True)
                        log(f"   Created directory: {dir_name}", ft.Colors.YELLOW)
                    try:
                        os.rename(filename, new_path)
                        fixed_any = True
                        log(f"   Fixed: {filename} → {new_path}", ft.Colors.YELLOW)
                    except OSError as e:
                        log(f"   Could not fix {filename}: {e}", ft.Colors.ORANGE)
            if fixed_any:
                log("   ✓ Filesystem repairs completed", ft.Colors.GREEN)
            else:
                log("   ✓ No repairs needed", ft.Colors.GREEN)
        except Exception as e:
            log(f"   Repair Warning: {e}", ft.Colors.ORANGE)
        
        log("4. Importing Modules...", ft.Colors.CYAN)
        
        try:
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
            
            try:
                from ui.firebase_mobile_login import FirebaseMobileLogin
                log("   ...Firebase mobile login OK")
            except ImportError:
                log("   ...Firebase mobile login not found (optional)", ft.Colors.YELLOW)
                FirebaseMobileLogin = None
            
            log("   ...OK")
            
        except ImportError as e:
            log(f"   IMPORT ERROR: {e}", ft.Colors.RED)
            import traceback
            log(f"   Traceback: {traceback.format_exc()}", ft.Colors.RED)
            return

        log("5. Loading Credentials...", ft.Colors.CYAN)
        
        creds_path = os.path.join(app_path, "services", "web.json")
        if not os.path.exists(creds_path):
            creds_path = os.path.join(cwd, "services", "web.json")
        if not os.path.exists(creds_path):
            creds_path = os.path.join(app_path, "web.json")
        if not os.path.exists(creds_path):
            creds_path = os.path.join(cwd, "web.json")
        
        log(f"   Checking: {creds_path}")
        
        if os.path.exists(creds_path):
            log(f"   ✓ Found credentials file", ft.Colors.GREEN)
            try:
                with open(creds_path, 'r') as f:
                    data = json.load(f)
                    config = data.get('web') or data.get('installed')
                    
                    if not config:
                        log("   ERROR: Invalid JSON format", ft.Colors.RED)
                        return
                    
                    client_id = config.get('client_id')
                    client_secret = config.get('client_secret')
                    redirect_uris = config.get('redirect_uris', [])
                    
                    platform = page.platform
                    is_mobile = platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
                    
                    if is_mobile:
                        redirect_url = "https://lms-callback.vercel.app/firebase_callback_v2.html"
                        log(f"   Platform: Mobile - Using Vercel callback", ft.Colors.CYAN)
                    else:
                        redirect_url = "http://localhost:8550/oauth_callback"
                        log(f"   Platform: Desktop - Using localhost", ft.Colors.CYAN)
                    
                    log(f"   ✓ Client ID: {client_id[:30]}...", ft.Colors.GREEN)
                    log(f"   ✓ Redirect URL: {redirect_url}", ft.Colors.GREEN)
                    
            except Exception as e:
                log(f"   ERROR loading credentials: {e}", ft.Colors.RED)
                return
        else:
            log(f"   ERROR: web.json not found!", ft.Colors.RED)
            log(f"   Searched: {creds_path}", ft.Colors.RED)
            return

        log("6. Initializing Auth Service...", ft.Colors.CYAN)
        auth_service = GoogleAuth(credentials_file=creds_path)
        log("   ✓ Auth Service initialized", ft.Colors.GREEN)
        
        log("7. All checks passed! Launching app...", ft.Colors.CYAN)
        time.sleep(2)  
        
        page.controls.clear()
        page.title = "LMS Alternative"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = ft.Colors.WHITE
        page.padding = 0

        from flet.auth.providers import GoogleOAuthProvider
        
        provider = GoogleOAuthProvider(
            client_id=client_id,
            client_secret=client_secret,
            redirect_url=redirect_url
        )
        provider.scopes = [
            "openid",
            "email",
            "profile"
        ]
        
        def handle_on_login(e):
            print("=" * 60)
            print("OAuth Callback Received")
            print("=" * 60)
            
            if e.error:
                print(f"Login error: {e.error}")
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Login Error: {e.error}"),
                    action="Dismiss"
                )
                page.snack_bar.open = True
                page.update()
                return
            
            if not hasattr(page.auth, 'token') or not page.auth.token:
                print("No auth token received")
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Authentication failed: No token received"),
                    action="Dismiss"
                )
                page.snack_bar.open = True
                page.update()
                return
            
            token_data = page.auth.token
            print(f"Token received")
            print(f"Token type: {type(token_data)}")
            
            if isinstance(token_data, dict):
                print(f"  Token keys: {list(token_data.keys())}")
                print(f"  Scope: {token_data.get('scope', 'N/A')}")
                
                token_data['client_id'] = client_id
                token_data['client_secret'] = client_secret
            
            print("Bridging token to auth service...")
            if auth_service.login_with_token(token_data):
                print("✓ Authentication successful!")
                show_dashboard()
            else:
                print("Failed to bridge token")
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Authentication failed: Could not complete login"),
                    action="Dismiss"
                )
                page.snack_bar.open = True
                page.update()
        
        page.on_login = handle_on_login
        
        def show_dashboard():
            page.controls.clear()
            dashboard = Dashboard(page, auth_service, handle_logout)
            if hasattr(dashboard, 'get_view'):
                page.add(dashboard.get_view())
            else:
                page.add(dashboard)
            page.update()
        
        def handle_logout():
            print("Logging out...")
            auth_service.logout()
            if hasattr(page.auth, 'logout'):
                page.auth.logout()
            show_login()
        
        def show_login():
            page.controls.clear()
            
            if is_mobile and FirebaseMobileLogin:
                print("→ Using Firebase mobile login")
                
                firebase_config_path = os.path.join(app_path, "services", "firebase_config.json")
                if not os.path.exists(firebase_config_path):
                    firebase_config_path = os.path.join(cwd, "services", "firebase_config.json")
                
                if os.path.exists(firebase_config_path):
                    with open(firebase_config_path, 'r') as f:
                        firebase_config = json.load(f)
                else:
                    firebase_config = {}
                
                page.add(FirebaseMobileLogin(
                    page, 
                    auth_service, 
                    firebase_config,
                    client_id,
                    on_success=show_dashboard
                ))
            else:
                print("→ Using standard OAuth login")
                page.add(LoginView(page, provider, auth_service, on_success=show_dashboard))
            
            page.update()
        
        print("\n" + "=" * 60)
        print("LMS Alternative Starting")
        print("=" * 60)
        print(f"Platform: {page.platform}")
        
        if auth_service.is_authenticated():
            print("✓ User already authenticated")
            show_dashboard()
        else:
            print("→ Showing login screen")
            show_login()
            
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        log(f"CRITICAL ERROR: {e}", ft.Colors.RED)
        log(f"Traceback:\n{error_msg}", ft.Colors.RED)
        print(f"CRITICAL ERROR:\n{error_msg}")
        
        time.sleep(10)

if __name__ == "__main__":
    ft.app(target=main)