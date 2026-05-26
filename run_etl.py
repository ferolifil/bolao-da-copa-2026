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

from cfg.api_credentials import local_oauth_flow
from etl.read import gsheets_to_df
from etl.load import df_to_drive_csv

# Scopes for Google Sheets and Drive
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

# NOTE: the notebook may run with cwd in /etl, so load .env from the project root if needed.
env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)

# Spreadsheets id and ranges are defined in the .env file as JSON, and loaded into a dictionary for easy access.
SPREADSHEETS = json.loads(os.getenv("SPREADSHEETS"))

# Authenticate.
# Prefer OAuth token from environment;
creds = None
OAUTH_TOKEN = os.getenv('OAUTH_TOKEN')

# Credential loading and refreshing logic is encapsulated in the local_oauth_flow function, which will handle both loading from OAUTH_TOKEN and refreshing if necessary.
creds = local_oauth_flow(OAUTH_TOKEN, SCOPES)

# Build services
SHEETS_SERVICE = build('sheets', 'v4', credentials=creds)
DRIVE_SERVICE = build('drive', 'v3', credentials=creds)

# Example usage: read a range from a spreadsheet into a DataFrame
df = gsheets_to_df(SPREADSHEETS['palpites_fg'], SHEETS_SERVICE)
print(df.head())

# Example usage: save a DataFrame to Google Drive as a CSV file
df_to_drive_csv(DRIVE_SERVICE, df, 'saida_teste.csv', folder_id='1K2IfAx1KvJsQmvvMD7wwolXMTPTgtKLt', overwrite=False)