import os
# import pickle # REMOVED
# from google_auth_oauthlib.flow import InstalledAppFlow # REMOVED
from google.auth.transport.requests import Request
from googleapiclient.discovery import build  # Add this import

SCOPES = ["https://www.googleapis.com/auth/drive"]

class GoogleAuth:
    def __init__(self):
        self.creds = None
        # Path for Desktop Auth flow
        self.credentials_file = os.path.join(os.path.dirname(__file__), "credentials.json")
        self.scopes = ["https://www.googleapis.com/auth/drive"]

    def login_desktop(self):
        """Standard OAuth flow for Desktop (Windows/Linux/Mac).
        Uses lazy import to prevent 'wsgiref' error on Android.
        """
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"credentials.json not found at {self.credentials_file}")

        # LAZY IMPORT: Only import this when running on Desktop!
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        flow = InstalledAppFlow.from_client_secrets_file(
            self.credentials_file, self.scopes
        )
        # Run local server (this is what triggers wsgiref)
        self.creds = flow.run_local_server(port=0)

    def set_credentials(self, credentials):
        """Sets the credentials after valid login via Flet (Android/Web)."""
        self.creds = credentials

    def is_authenticated(self):
        return self.creds is not None and self.creds.valid

    def logout(self):
        self.creds = None

    def get_service(self):
        return build('drive', 'v3', credentials=self.creds)

    def get_user_info(self):
        try:
            service = build('drive', 'v3', credentials=self.creds)
            about = service.about().get(fields="user").execute()
            return about.get('user', {})
        except Exception as e:
            print(f"Error getting user info: {e}")
            return {}