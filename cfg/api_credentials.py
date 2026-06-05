from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import json

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


def service_account_flow(service_account_info, scopes) -> Credentials:
    """
    Performs the OAuth 2.0 flow using a service account to obtain credentials for Google APIs.

    This function loads service account credentials from a specified JSON file and returns an instance of
    google.oauth2.service_account.Credentials that can be used to authenticate API requests.

    Parameters
    ----------
    service_account_info : str
        The JSON string containing the service account credentials.
    scopes : list
        A list of scopes that specify the level of access requested for the credentials.

    Returns
    -------
    Credentials
        An instance of google.oauth2.service_account.Credentials containing the authenticated service account credentials.

    Raises
    ------
    SystemExit
        If there is an error loading the service account credentials or if the file is not found.
    """
    try:
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )
        return creds
    except Exception as exc:
        raise SystemExit(f'Failed to load service account credentials: {exc}')