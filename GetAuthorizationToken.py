import requests
import json
class TokenGetter:
    def __init__(self, tid):
        self.token_url = f"https://login.microsoftonline.com/{tid}/oauth2/v2.0/token"

    def get_token(self, appData : json, scope) -> str:
        payload = {
            'grant_type': 'client_credentials',
            'client_id': appData["ClientId"],
            'client_secret': appData["ClientSecret"],
            'scope': [scope]
        }
        
        response = requests.post(self.token_url, data=payload)
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            return None
