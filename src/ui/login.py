import flet as ft

class LoginView(ft.Column):
    def __init__(self, page, provider, auth_service, on_success=None):
        super().__init__(
            controls=[],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            spacing=20
        )

        self.page = page
        self.provider = provider
        self.auth = auth_service
        self.on_success = on_success
        
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
                "Access your learning materials anywhere",
                size=16,
                color=ft.Colors.GREY_700,
                text_align=ft.TextAlign.CENTER
            )
        )
        
        platform_name = self._get_platform_name(self.page.platform)
        self.controls.append(ft.Container(height=10))
        self.controls.append(
            ft.Text(
                f"Platform: {platform_name}",
                size=12,
                color=ft.Colors.GREY_600,
                text_align=ft.TextAlign.CENTER
            )
        )
        
        self.status_text = ft.Text(
            "Please log in to continue",
            color=ft.Colors.GREY_700,
            text_align=ft.TextAlign.CENTER
        )
        self.controls.append(ft.Container(height=20))
        self.controls.append(self.status_text)
        
        self.login_button = ft.ElevatedButton(
            text="Login with Google",
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
        
        self.controls.append(ft.Container(height=20))
        self.controls.append(
            ft.Text(
                "Secure authentication via Google OAuth 2.0",
                size=12,
                color=ft.Colors.GREY_500,
                text_align=ft.TextAlign.CENTER,
                italic=True
            )
        )

    def _get_platform_name(self, platform):
        platform_map = {
            ft.PagePlatform.WINDOWS: "Windows",
            ft.PagePlatform.LINUX: "Linux",
            ft.PagePlatform.MACOS: "macOS",
            ft.PagePlatform.ANDROID: "Android",
            ft.PagePlatform.IOS: "iOS"
        }
        return platform_map.get(platform, str(platform))

    def handle_login(self, e):
        platform = self.page.platform
        print(f"\n{'='*60}")
        print(f"Login initiated on platform: {platform}")
        print(f"{'='*60}")

        is_desktop = platform in [
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.LINUX,
            ft.PagePlatform.MACOS
        ]

        if is_desktop:
            self.status_text.value = "Opening browser for authentication..."
            self.status_text.color = ft.Colors.BLUE_600
            self.login_button.disabled = True
            self.page.update()
            
            try:
                print("→ Starting desktop OAuth flow...")
                self.auth.login_desktop()
                
                if self.auth.is_authenticated():
                    self.status_text.value = "Login successful!"
                    self.status_text.color = ft.Colors.GREEN_600
                    self.page.update()
                    print("✓ Desktop login successful")
                    
                    if self.on_success:
                        self.on_success()
                else:
                    self.status_text.value = "Login completed but authentication failed"
                    self.status_text.color = ft.Colors.RED_600
                    self.login_button.disabled = False
                    self.page.update()
                     
            except Exception as ex:
                import traceback
                error_msg = str(ex)
                self.status_text.value = f"Login failed: {error_msg[:50]}..."
                self.status_text.color = ft.Colors.RED_600
                self.login_button.disabled = False
                self.page.update()
                print(f"Desktop login error: {ex}")
                print(f"Traceback:\n{traceback.format_exc()}")

        else:
            print(f"\n{'='*60}")
            print("MOBILE OAUTH FLOW")
            print(f"{'='*60}")
            print(f"Platform detected: {platform}")
            
            self.status_text.value = f"Mobile OAuth Flow\nPlatform: {platform}\nChecking provider..."
            self.status_text.color = ft.Colors.BLUE_600
            self.login_button.disabled = True
            self.page.update()
            
            import time
            time.sleep(1)
            
            try:
                import urllib.parse
                
                self.status_text.value = f"Building OAuth URL...\nRedirect: {self.provider.redirect_url}"
                self.page.update()
                time.sleep(1)
                
                print(f"→ Building OAuth URL for manual browser launch...")
                print(f"  Client ID: {self.provider.client_id[:30] if self.provider.client_id else 'MISSING'}...")
                print(f"  Redirect URL: {self.provider.redirect_url}")
                print(f"  Scopes: {self.provider.scopes}")
                
                auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
                params = {
                    'client_id': self.provider.client_id,
                    'redirect_uri': self.provider.redirect_url,
                    'response_type': 'code',
                    'scope': ' '.join(self.provider.scopes),
                    'access_type': 'offline',
                    'prompt': 'consent'
                }
                
                oauth_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
                
                print(f"→ Full OAuth URL: {oauth_url}")
                
                self.status_text.value = f"Opening browser...\n\nRedirect URI:\n{self.provider.redirect_url}\n\nIf you get 'redirect_uri_mismatch',\nadd this EXACT URL to Google Cloud Console"
                self.status_text.color = ft.Colors.ORANGE
                self.page.update()
                time.sleep(3)  
                
                print(f"\n→ Launching browser with OAuth URL using page.launch_url()...")
                
                self.page.launch_url(oauth_url)
                
                print("✓ Browser launch requested!")
                
                self.status_text.value = "✓ Browser should open!\n\n1. Sign in with Google\n2. You'll see 'Login Successful!'\n3. Close browser\n4. Return to app\n\nNote: Auto-login not available on mobile"
                self.status_text.color = ft.Colors.BLUE_600
                self.login_button.disabled = False  
                self.page.update()
                
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Browser opening... Complete sign-in, then return here."),
                    action="OK"
                )
                self.page.snack_bar.open = True
                self.page.update()
                
            except Exception as ex:
                import traceback
                error_msg = str(ex)
                traceback_str = traceback.format_exc()
                print(f"Browser launch error: {ex}")
                print(f"Traceback:\n{traceback_str}")
                
                self.status_text.value = f"Error opening browser:\n{error_msg[:100]}"
                self.status_text.color = ft.Colors.RED_600
                self.login_button.disabled = False
                self.page.update()