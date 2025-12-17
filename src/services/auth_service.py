import os
import pickle
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]

class GoogleAuth:
    def __init__(self, credentials_file=None):
        self.creds = None
        self.credentials_file = credentials_file or os.path.join(
            os.path.dirname(__file__), 
            "web.json"
        )
        self.token_file = os.path.join(os.path.dirname(__file__), "token.pickle")
        
        # Load client info from credentials file
        self.client_id = None
        self.client_secret = None
        self._load_client_info()
        
        # Try to load existing credentials
        self._load_credentials()

    def _load_client_info(self):
        """Load client_id and client_secret from credentials file"""
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    data = json.load(f)
                    config = data.get('web') or data.get('installed')
                    if config:
                        self.client_id = config.get('client_id')
                        self.client_secret = config.get('client_secret')
                        print(f"✓ Loaded client info from {os.path.basename(self.credentials_file)}")
            except Exception as e:
                print(f"❌ Error loading client info: {e}")

    def _load_credentials(self):
        """Load credentials from token file if it exists"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
                print("✓ Loaded existing credentials from token.pickle")
            except Exception as e:
                print(f"⚠ Error loading token: {e}")
                self.creds = None

    def _save_credentials(self):
        """Save credentials to token file"""
        try:
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)
            print("✓ Credentials saved to token.pickle")
        except Exception as e:
            print(f"❌ Error saving token: {e}")

    def login_desktop(self):
        """Perform Google OAuth login (Desktop only - uses run_local_server)"""
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_file}")
            
        # Lazy import to avoid wsgiref/Android issues
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        print("Starting desktop OAuth flow...")
        flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
        
        # Use port 8550 to match redirect URI
        self.creds = flow.run_local_server(port=8550)
        
        # Save credentials for future use
        self._save_credentials()
        print("✓ Desktop login successful")

    def login_with_token(self, token_data):
        """
        Create credentials from Flet's auth token (Mobile/Web).
        token_data: dict containing access_token, etc. from page.auth.token
        """
        try:
            print("→ Bridging OAuth token to Google credentials")
            print(f"  Token data type: {type(token_data)}")
            
            if not isinstance(token_data, dict):
                print("❌ Token data is not a dictionary")
                return False
            
            # Extract token information
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            
            if not access_token:
                print("❌ No access_token in token_data")
                return False
            
            # Get client credentials
            client_id = token_data.get("client_id") or self.client_id
            client_secret = token_data.get("client_secret") or self.client_secret
            
            # Handle scope - can be string or list
            scope = token_data.get("scope", SCOPES)
            if isinstance(scope, str):
                # Split space-separated scope string into list
                scope = scope.split() if scope else SCOPES
            
            print(f"  ✓ Access token: present")
            print(f"  ✓ Refresh token: {'present' if refresh_token else 'missing'}")
            print(f"  ✓ Client ID: {'present' if client_id else 'missing'}")
            print(f"  ✓ Client secret: {'present' if client_secret else 'missing'}")
            print(f"  ✓ Scopes: {', '.join(scope) if isinstance(scope, list) else scope}")
            
            # Reconstruct Credentials object
            self.creds = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=scope
            )
            
            # Verify credentials are valid
            if not self.creds.valid:
                print("⚠ Created credentials are not currently valid")
                # Try to refresh if we have a refresh token
                if self.creds.expired and self.creds.refresh_token:
                    print("→ Attempting to refresh expired token...")
                    try:
                        self.creds.refresh(Request())
                        print("✓ Token refreshed successfully")
                    except Exception as refresh_error:
                        print(f"❌ Failed to refresh token: {refresh_error}")
                        return False
            else:
                print("✓ Credentials are valid")
            
            # Save credentials for future use
            self._save_credentials()
            return True
            
        except Exception as e:
            import traceback
            print(f"❌ Error bridging token: {e}")
            print(f"Traceback:\n{traceback.format_exc()}")
            return False

    def is_authenticated(self):
        """Check if user is authenticated with valid credentials"""
        if self.creds is None:
            return False
        
        # Check if credentials are expired and refresh if needed
        if self.creds.expired:
            if self.creds.refresh_token:
                try:
                    print("→ Refreshing expired credentials...")
                    self.creds.refresh(Request())
                    self._save_credentials()
                    print("✓ Credentials refreshed")
                    return True
                except Exception as e:
                    print(f"❌ Error refreshing token: {e}")
                    return False
            else:
                print("⚠ Credentials expired and no refresh token available")
                return False
        
        return self.creds.valid

    def logout(self):
        """Clear credentials and delete token file"""
        print("→ Logging out...")
        self.creds = None
        if os.path.exists(self.token_file):
            try:
                os.remove(self.token_file)
                print("✓ Token file removed")
            except Exception as e:
                print(f"❌ Error removing token file: {e}")

    def get_service(self):
        """Get Google Drive service instance"""
        if not self.is_authenticated():
            print("❌ Cannot get service - not authenticated")
            return None
        
        try:
            service = build('drive', 'v3', credentials=self.creds)
            print("✓ Google Drive service created")
            return service
        except Exception as e:
            print(f"❌ Error creating service: {e}")
            return None

    def get_user_info(self):
        """Get current user information"""
        try:
            service = self.get_service()
            if not service:
                return {}
            about = service.about().get(fields="user").execute()
            user = about.get('user', {})
            email = user.get('emailAddress', 'unknown')
            print(f"✓ User info retrieved: {email}")
            return user
        except Exception as e:
            print(f"❌ Error getting user info: {e}")
            return {}