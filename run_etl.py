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

def gsheets_to_df(sheet_id, range) -> pd.DataFrame:
    """
    Reads data from a Google Sheets range and returns it as a pandas DataFrame.

    Parameters
    ----------
    sheet_id : str
        The ID of the Google Sheets document.
    range : str
        The A1 notation of the values to retrieve (e.g., 'Sheet1!A1:C100').

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the sheet data, where the first row is used as column headers.
        If no data is found, an empty DataFrame is returned.
    """
    # Initialize the Google Sheets API client
    sheet = SHEETS_SERVICE.spreadsheets()

    # Fetch values from the specified spreadsheet and range
    result = sheet.values().get(
        spreadsheetId=sheet_id,
        range=range
    ).execute()

    # Extract the values from the response (list of rows)
    values = result.get('values', [])

    # Convert to DataFrame:
    # - First row becomes column names
    # - Remaining rows become data
    return pd.DataFrame(data=values[1:], columns=values[0])


# Scopes for Google Sheets and Drive
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

# NOTE: the notebook may run with cwd in /etl, so load .env from the project root if needed.
env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)

SPREADSHEETS = json.loads(os.getenv("SPREADSHEETS"))
print(f"1 -> {SPREADSHEETS['palpites_fg'][0]}")  # Debug: print the first spreadsheet ID to verify it's loaded correctly (remove in production!)

# Authenticate.
# Prefer OAuth token from environment; otherwise fall back to local token.json or service account.
creds = None
OAUTH_TOKEN = os.getenv('OAUTH_TOKEN')

print(f"2 -> {OAUTH_TOKEN}")   # Debug: print the OAUTH_TOKEN to verify it's loaded correctly (remove in production!)

if OAUTH_TOKEN:
    try:
        # Authenticate using the token data
        token_data = json.loads(OAUTH_TOKEN)
        creds = Credentials.from_authorized_user_info(token_data, scopes=SCOPES)
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
    
# Build services
SHEETS_SERVICE = build('sheets', 'v4', credentials=creds)
DRIVE_SERVICE = build('drive', 'v3', credentials=creds)

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1pZAAw9L8FvPQnad5ejfM7gu_JCeuwuEy7AqGiA5wKy0'
SAMPLE_RANGE_NAME = 'palpites_fg!A1:ET20'

df = gsheets_to_df(SPREADSHEETS['palpites_fg'][0], SPREADSHEETS['palpites_fg'][1])
print(df.head())

# import time
# time.sleep(10)
