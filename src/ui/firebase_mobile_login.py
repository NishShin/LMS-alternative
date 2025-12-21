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
        
        self.firebase_db_url = firebase_config.get('databaseURL')
        if not self.firebase_db_url:
            self.firebase_db_url = f"https://{firebase_config['projectId']}-default-rtdb.firebaseio.com"
        
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
                "Powered by Firebase",
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
        print(f"\n{'='*60}")
        print(f"Firebase OAuth login initiated")
        print(f"{'='*60}")

        self.session_id = secrets.token_urlsafe(16)
        print(f"Session ID: {self.session_id}")
        print(f"Firebase DB URL: {self.firebase_db_url}")
        
        self.status_text.value = f"📱 SESSION ID:\n{self.session_id}\n\nOpening browser..."
        self.status_text.color = ft.Colors.ORANGE
        self.status_text.size = 16
        self.status_text.weight = ft.FontWeight.BOLD
        self.login_button.disabled = True
        self.progress.visible = True
        self.page.update()
        
        time.sleep(3)
        
        try:
            callback_page_url = self._create_callback_page_url()
            
            auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
            params = {
                'client_id': self.oauth_client_id,
                'redirect_uri': callback_page_url,
                'response_type': 'token',
                'scope': 'openid email profile https://www.googleapis.com/auth/drive',
                'state': self.session_id
            }
            
            oauth_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
            
            print(f"✓ OAuth URL created")
            print(f"✓ Session ID in URL: {self.session_id}")
            print(f"✓ Callback page: {callback_page_url}")
            print(f"✓ Full OAuth URL: {oauth_url[:150]}...")
            
            self.status_text.value = "Opening browser...\n\nAfter signing in,\nclose browser and return here"
            self.page.update()
            
            time.sleep(1)
            
            print(f"→ Launching browser...")
            self.page.launch_url(oauth_url)
            print(f"✓ Browser launched")
            
            self.status_text.value = "✓ Browser opened!\n\nWaiting for sign-in...\n(Auto-detecting)"
            self.status_text.color = ft.Colors.BLUE_600
            self.page.update()
            
            self._start_polling()
            
        except Exception as ex:
            import traceback
            print(f"❌ Error: {ex}")
            print(f"Traceback:\n{traceback.format_exc()}")
            self.status_text.value = f"❌ Error:\n{str(ex)[:100]}"
            self.status_text.color = ft.Colors.RED_600
            self.login_button.disabled = False
            self.progress.visible = False
            self.page.update()
    
    def _create_callback_page_url(self):
        return f"https://lms-callback.vercel.app/firebase_callback_v2.html"
    
    def _start_polling(self):
        import threading
        
        self.polling = True
        
        def poll():
            max_attempts = 60
            attempt = 0
            
            self.page.run_task(self._show_polling_started)
            
            while self.polling and attempt < max_attempts:
                self.page.run_task(self._update_waiting_status, attempt)
                
                try:
                    check_url = f"{self.firebase_db_url}/oauth_sessions/{self.session_id}.json"
                    print(f"→ Polling Firebase attempt {attempt + 1}/{max_attempts}")
                    print(f"  Session ID: {self.session_id}")
                    print(f"  Firebase DB URL: {self.firebase_db_url}")
                    print(f"  Full check URL: {check_url}")
                    
                    req = urllib.request.Request(check_url)
                    try:
                        with urllib.request.urlopen(req, timeout=5) as response:
                            response_text = response.read().decode('utf-8')
                            status_code = response.status
                            
                            try:
                                with open('/storage/emulated/0/Download/firebase_debug.txt', 'a') as f:
                                    f.write(f"\n\n=== Attempt {attempt + 1} ===\n")
                                    f.write(f"Status: {status_code}\n")
                                    f.write(f"Response: {response_text}\n")
                            except:
                                pass
                                
                    except urllib.error.HTTPError as he:
                        status_code = he.code
                        response_text = ""
                        print(f"  HTTP Error: {status_code}")
                    
                    print(f"  Response status: {status_code}")
                    print(f"  Response text length: {len(response_text)}")
                    print(f"  Response preview: {response_text[:200] if response_text else 'empty'}")
                    
                    if status_code == 200:
                        data = json.loads(response_text) if response_text and response_text != 'null' else None
                        
                        if data and isinstance(data, dict) and 'access_token' in data:
                            print(f"✓ Tokens found in Firebase!")
                            
                            print(f"  Deleting session from Firebase...")
                            try:
                                del_req = urllib.request.Request(check_url, method='DELETE')
                                urllib.request.urlopen(del_req)
                            except Exception as del_err:
                                print(f"  Warning: Could not delete session: {del_err}")
                            
                            self.page.run_task(self._handle_tokens, data)
                            return
                        else:
                            print(f"  No tokens yet (data is null or missing access_token)")
                    
                    time.sleep(5)
                    attempt += 1
                    
                except Exception as e:
                    print(f"⚠ Polling error: {e}")
                    time.sleep(5)
                    attempt += 1
            
            if attempt >= max_attempts:
                print(f"⏱ Polling timeout")
                self.page.run_task(self._handle_timeout)
        
        thread = threading.Thread(target=poll, daemon=True)
        thread.start()
    
    async def _show_firebase_response(self, response_preview, data):
        has_token = "YES" if (data and isinstance(data, dict) and 'access_token' in data) else "NO"
        self.status_text.value = f"📱 SESSION: {self.session_id[:10]}...\n\n🔍 FIREBASE SAYS:\n{response_preview}\n\nHas token? {has_token}"
        self.status_text.size = 12
        self.page.update()
    
    async def _show_polling_started(self):
        self.status_text.value = f"📱 SESSION: {self.session_id}\n\n🔄 POLLING STARTED\nCheck #1/60"
        self.page.update()
    
    async def _update_waiting_status(self, attempt):
        dots = "." * ((attempt % 3) + 1)
        self.status_text.value = f"📱 SESSION: {self.session_id}\n\nWaiting for sign-in{dots}\nCheck #{attempt + 1}/60"
        self.status_text.size = 14
        self.status_text.weight = ft.FontWeight.NORMAL
        self.page.update()
    
    async def _handle_tokens(self, tokens):
        print(f"→ Processing tokens from Firebase...")
        
        self.polling = False
        
        self.status_text.value = "✓ Signed in!\n\nProcessing authentication..."
        self.status_text.color = ft.Colors.GREEN_600
        self.page.update()
        
        token_data = {
            'access_token': tokens.get('access_token'),
            'token_type': tokens.get('token_type', 'Bearer'),
            'expires_in': tokens.get('expires_in'),
            'scope': tokens.get('scope')
        }
        
        if self.auth.login_with_token(token_data):
            self.status_text.value = "Authentication complete!"
            self.progress.visible = False
            self.page.update()
            
            time.sleep(1)
            
            if self.on_success:
                self.on_success()
        else:
            self.status_text.value = "Authentication failed\n\nPlease try again"
            self.status_text.color = ft.Colors.RED_600
            self.login_button.disabled = False
            self.progress.visible = False
            self.page.update()
    
    async def _handle_timeout(self):
        self.polling = False
        self.status_text.value = "Timeout\n\nSign-in took too long.\nPlease try again."
        self.status_text.color = ft.Colors.ORANGE
        self.login_button.disabled = False
        self.progress.visible = False
        self.page.update()