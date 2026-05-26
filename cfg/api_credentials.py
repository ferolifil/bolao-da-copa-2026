import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
import io
import os
import os.path
import json
from dotenv import load_dotenv

def local_oauth_flow(oauth_token, scopes) -> Credentials:
    """
    Performs the OAuth 2.0 flow to obtain user credentials for Google APIs.

    This function checks for existing credentials in 'token.json'. If valid credentials are found, they are returned.
    If the credentials are expired but refreshable, they are refreshed. Otherwise, a new OAuth flow is initiated,
    prompting the user to authenticate and authorize access. The obtained credentials are then saved to 'token.json'
    for future use.

    Returns
    -------
    Credentials
        An instance of google.oauth2.credentials.Credentials containing the authenticated user's credentials.

    Raises
    ------
    SystemExit
        If there is an error during the authentication process or if the obtained credentials are invalid.
    """
    creds = None

    if oauth_token:
        try:
            # Authenticate using the token data
            token_data = json.loads(oauth_token)
            creds = Credentials.from_authorized_user_info(token_data, scopes=scopes)
        except Exception as exc:
            raise SystemExit(f'Failed to load OAUTH_TOKEN: {exc}')
    else:
        raise SystemExit('No credentials found. Please provide OAUTH_TOKEN, token.json, or service_account.json.')

    # Refresh if needed
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise SystemExit('Credentials are invalid and cannot be refreshed. Please re-authenticate.')

    return creds