import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]

class GoogleAuth:
    def __init__(self):
        self.creds = None

    def login(self, page):
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        self.creds = flow.run_local_server(port=0)
        page.update()

    def get_service(self):
        return build("drive", "v3", credentials=self.creds)

    def is_authenticated(self):
        return self.creds is not None
