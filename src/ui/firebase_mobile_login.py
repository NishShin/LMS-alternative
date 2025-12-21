import flet as ft
import time
import urllib.parse
import urllib.request
import json
import secrets
import threading

class FirebaseMobileLogin(ft.Column):
    def __init__(self, page, auth_service, firebase_config, oauth_client_id, on_success=None):
        super().__init__(
            controls=[],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            spacing=20
        )

        self.page = page
        self.auth = auth_service
        self.firebase_config = firebase_config
        self.oauth_client_id = oauth_client_id
        self.on_success = on_success
        self.session_id = None
        self.polling = False
        
        self._build_ui()

    def _build_ui(self):
        self.controls.append(ft.Container(height=50))
        self.controls.append(
            ft.Icon(
                ft.Icons.CLOUD_CIRCLE,
                size=100,
                color=ft.Colors.BLUE_600
            )
        )
        
        self.controls.append(
            ft.Text(
                "Learning Management System",
                size=32,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER
            )
        )
        
        self.controls.append(
            ft.Text(
                "Mobile Login",
                size=16,
                color=ft.Colors.GREY_700,
                text_align=ft.TextAlign.CENTER
            )
        )
        
        self.status_text = ft.Text(
            "Sign in with your Google account",
            color=ft.Colors.GREY_700,
            text_align=ft.TextAlign.CENTER
        )
        self.controls.append(ft.Container(height=20))
        self.controls.append(self.status_text)
        
        self.debug_text = ft.Text(
            "",
            size=10,
            color=ft.Colors.GREY_500,
            text_align=ft.TextAlign.CENTER
        )
        self.controls.append(self.debug_text)
        
        self.login_button = ft.ElevatedButton(
            text="Sign in with Google",
            icon=ft.Icons.LOGIN,
            on_click=self.handle_login,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_600,
                color=ft.Colors.WHITE,
                padding=ft.padding.symmetric(horizontal=30, vertical=15),
            ),
            height=50
        )
        self.controls.append(ft.Container(height=10))
        self.controls.append(self.login_button)
        
        self.progress = ft.ProgressRing(visible=False)
        self.controls.append(self.progress)

    def handle_login(self, e):
        self.session_id = secrets.token_urlsafe(16)
        
        self.status_text.value = f"Opening browser..."
        self.status_text.color = ft.Colors.ORANGE
        self.status_text.size = 16
        self.status_text.weight = ft.FontWeight.BOLD
        self.login_button.disabled = True
        self.progress.visible = True
        self.page.update()
        
        time.sleep(2)
        
        try:
            auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
            params = {
                'client_id': self.oauth_client_id,
                'redirect_uri': 'https://lms-callback-git-main-astrallibertads-projects.vercel.app/callback.html',
                'response_type': 'token',
                'scope': 'openid email profile https://www.googleapis.com/auth/drive',
                'state': self.session_id
            }
            
            oauth_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
            
            self.status_text.value = "Opening browser...\n\nSign in and return to app"
            self.page.update()
            
            time.sleep(1)
            
            self.page.launch_url(oauth_url)
            
            self.status_text.value = "✓ Browser opened!\n\nWaiting for sign-in..."
            self.status_text.color = ft.Colors.BLUE_600
            self.debug_text.value = f"Session: {self.session_id[:8]}..."
            self.page.update()
            
            self._start_polling()
            
        except Exception as ex:
            self.status_text.value = f"❌ Error:\n{str(ex)[:100]}"
            self.status_text.color = ft.Colors.RED_600
            self.login_button.disabled = False
            self.progress.visible = False
            self.page.update()
    
    def _log(self, msg):
        try:
            self.page.run_task(self._update_debug, msg)
        except:
            pass
    
    async def _update_debug(self, msg):
        self.debug_text.value = msg
        self.page.update()
    
    def _start_polling(self):
        self.polling = True
        
        def poll():
            max_attempts = 60
            attempt = 0
            
            while self.polling and attempt < max_attempts:
                self.page.run_task(self._update_waiting_status, attempt)
                
                try:
                    check_url = f"https://lms-callback.vercel.app/api/token/{self.session_id}"
                    
                    self._log(f"Check #{attempt+1}/60")
                    
                    req = urllib.request.Request(check_url)
                    req.add_header('Accept', 'application/json')
                    
                    try:
                        with urllib.request.urlopen(req, timeout=10) as response:
                            response_text = response.read().decode('utf-8')
                            data = json.loads(response_text)
                            
                            if data.get('success') and data.get('token'):
                                token_info = data['token']
                                if token_info.get('access_token'):
                                    self._log(f"✓ Token found!")
                                    self.page.run_task(self._handle_tokens, token_info)
                                    return
                            
                            self._log(f"Check #{attempt+1}: Waiting...")
                            
                    except urllib.error.HTTPError as he:
                        if he.code == 404:
                            self._log(f"Check #{attempt+1}: Not ready")
                        else:
                            self._log(f"Check #{attempt+1}: HTTP {he.code}")
                            
                    except Exception as conn_err:
                        self._log(f"Check #{attempt+1}: Connection issue")
                    
                    time.sleep(5)
                    attempt += 1
                    
                except Exception as e:
                    self._log(f"Check #{attempt+1}: Error")
                    time.sleep(5)
                    attempt += 1
            
            if attempt >= max_attempts:
                self.page.run_task(self._handle_timeout)
        
        thread = threading.Thread(target=poll, daemon=True)
        thread.start()
    
    async def _update_waiting_status(self, attempt):
        dots = "." * ((attempt % 3) + 1)
        self.status_text.value = f"Waiting for sign-in{dots}\nCheck #{attempt + 1}/60"
        self.status_text.size = 14
        self.status_text.weight = ft.FontWeight.NORMAL
        self.page.update()
    
    async def _handle_tokens(self, tokens):
        self.polling = False
        
        self.status_text.value = "✓ Token received!\n\nAuthenticating..."
        self.status_text.color = ft.Colors.GREEN_600
        self.debug_text.value = "Processing..."
        self.page.update()
        
        token_data = {
            'access_token': tokens.get('access_token'),
            'token_type': tokens.get('token_type', 'Bearer'),
            'expires_in': tokens.get('expires_in'),
            'scope': tokens.get('scope'),
            'client_id': self.oauth_client_id,
            'client_secret': self.auth.client_secret
        }
        
        auth_result = self.auth.login_with_token(token_data)
        
        if auth_result:
            self.status_text.value = "✓ Authentication complete!"
            self.status_text.color = ft.Colors.GREEN_600
            self.progress.visible = False
            self.debug_text.value = "Loading dashboard..."
            self.page.update()
            
            time.sleep(1)
            
            if self.on_success:
                self.on_success()
        else:
            self.status_text.value = "Authentication failed\n\nPlease try again"
            self.status_text.color = ft.Colors.RED_600
            self.login_button.disabled = False
            self.progress.visible = False
            self.debug_text.value = "Auth bridge failed"
            self.page.update()
    
    async def _handle_timeout(self):
        self.polling = False
        self.status_text.value = "Timeout\n\nSign-in took too long"
        self.status_text.color = ft.Colors.ORANGE
        self.login_button.disabled = False
        self.progress.visible = False
        self.debug_text.value = "Please try again"
        self.page.update()