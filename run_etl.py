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
from etl.read import gsheets_to_df, drive_csv_to_df, check_run_round
from etl.load import df_to_drive_csv
from etl.transform import calculate_points, normalize_df, tips_processing

# Scopes for Google Sheets and Drive
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
# NOTE: the notebook may run with cwd in /etl, so load .env from the project root if needed.
env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)
# Spreadsheets id and ranges are defined in the .env file as JSON, and loaded into a dictionary for easy access.
SPREADSHEETS = json.loads(os.getenv("SPREADSHEETS"))
PROCESSED_FOLDER_ID = os.getenv("PROCESSED_FOLDER_ID")
# Authenticate.
OAUTH_TOKEN = os.getenv('OAUTH_TOKEN')
# Credential loading and refreshing logic is encapsulated in the local_oauth_flow function, which will handle both loading from OAUTH_TOKEN 
# and refreshing if necessary.
creds = local_oauth_flow(OAUTH_TOKEN, SCOPES)
# Build services
SHEETS_SERVICE = build('sheets', 'v4', credentials=creds)
DRIVE_SERVICE = build('drive', 'v3', credentials=creds)
# Read data from Google Sheets into pandas DataFrames using the gsheets_to_df function.
df_palpites = gsheets_to_df(SPREADSHEETS['palpites_fg'], SHEETS_SERVICE)
df_gabarito = gsheets_to_df(SPREADSHEETS['gabarito'], SHEETS_SERVICE)
# Normalize dataframes
df_palpites = normalize_df(df_palpites)
df_gabarito = normalize_df(df_gabarito)
# Determine the current round by checking the count of non-empty entries in the gabarito DataFrame, which contains the correct answers for each match. 
# The minimum count across all columns gives an indication of how many rounds have been completed.
round_check = min(df_gabarito.count().to_list())
# Process the tips DataFrame to calculate predicted results and prepare it for comparison with the actual results.
df_palpites_f = tips_processing(df_palpites)
# Calculate points for each player based on their predictions and the actual results, 
# and print the resulting DataFrame with player rankings and scores.
df_points = calculate_points(df_palpites_f, df_gabarito, round_check)
# Load DataFrame to Google Drive as a CSV file using the df_to_drive_csv function
df_to_drive_csv(DRIVE_SERVICE, df_palpites_f, 'palpites.csv', PROCESSED_FOLDER_ID, overwrite=True)
if check_run_round(round_check, DRIVE_SERVICE, "1kYkENHRLwAvLiPGGamikFDzifR5KYRzh"):
    df_to_drive_csv(DRIVE_SERVICE, df_points, 'ranking_hst.csv', PROCESSED_FOLDER_ID, overwrite=False)