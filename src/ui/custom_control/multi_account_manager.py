import json
import os


class MultiAccountManager:
    def __init__(self, storage_path="storage/accounts.json"):
        self.storage_path = storage_path
        self.accounts = self.load_accounts()
        self.current_account = None
    
    def load_accounts(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_accounts(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.accounts, f, indent=2)
    
    def add_account(self, email, user_info, token_data=None, save_credentials=True):
        self.accounts[email] = {
            "user_info": user_info,
            "token_data": token_data if save_credentials else None,
            "save_credentials": save_credentials
        }
        self.save_accounts()
        print(f"Account added: {email} (Credentials saved: {save_credentials})")
    
    def update_account_credentials(self, email, token_data):
        if email in self.accounts:
            self.accounts[email]["token_data"] = token_data
            self.accounts[email]["save_credentials"] = True
            self.save_accounts()
    
    def remove_account(self, email):
        if email in self.accounts:
            del self.accounts[email]
            self.save_accounts()
            print(f"Account removed: {email}")
    
    def get_account(self, email):
        return self.accounts.get(email)
    
    def get_all_accounts(self):
        return list(self.accounts.keys())
    
    def has_saved_credentials(self, email):
        account = self.accounts.get(email)
        if account:
            return account.get("save_credentials", False) and account.get("token_data") is not None
        return False
    
    def set_current_account(self, email):
        self.current_account = email
    
    def get_current_account(self):
        return self.current_account