import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from database import get_oauth_tokens, save_oauth_tokens

CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = os.environ["GOOGLE_REDIRECT_URI"]
OWNER_USER_ID = os.environ.get("OWNER_USER_ID", "owner")

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar",
]

CLIENT_CONFIG = {
    "web": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [REDIRECT_URI],
    }
}


def build_authorize_url(state: str = "default") -> str:
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url


def handle_callback(code: str) -> Credentials:
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.fetch_token(code=code)
    creds = flow.credentials
    save_oauth_tokens(
        provider="google",
        user_id=OWNER_USER_ID,
        access_token=creds.token,
        refresh_token=creds.refresh_token,
        expiry=int(creds.expiry.timestamp()) if creds.expiry else None,
        scopes=" ".join(creds.scopes or []),
    )
    return creds


def get_user_credentials(user_id: str | None = None) -> Credentials | None:
    user_id = user_id or OWNER_USER_ID
    row = get_oauth_tokens("google", user_id)
    if not row:
        return None
    creds = Credentials(
        token=row["access_token"],
        refresh_token=row["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=(row["scopes"] or "").split(),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_oauth_tokens(
            provider="google",
            user_id=user_id,
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            expiry=int(creds.expiry.timestamp()) if creds.expiry else None,
            scopes=" ".join(creds.scopes or []),
        )
    return creds
