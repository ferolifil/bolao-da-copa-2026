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
# Local imports
from cfg.api_credentials import service_account_flow
from etl.extract import gsheets_to_df, check_run_round, drive_csv_to_df
from etl.load import df_to_drive_csv, df_to_gsheet
from etl.transform import calculate_points, normalize_df, tips_processing, make_base_table

# Scopes for Google Sheets and Drive
SCOPES = [
'https://www.googleapis.com/auth/spreadsheets',
'https://www.googleapis.com/auth/drive'
]
# NOTE: the notebook may run with cwd in /etl, so load .env from the project root if needed.
env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)
# Spreadsheets id and ranges are defined in the .env file as JSON, and loaded into a dictionary for easy access.
SPREADSHEETS = json.loads(os.getenv("SPREADSHEETS"))
PROCESSED_FOLDER_ID = os.getenv("PROCESSED_FOLDER_ID")
# Authenticate.
service_account_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT'))
# Credential loading and refreshing logic is encapsulated in the service_account_flow function, which will handle both loading from the service account info
# and refreshing if necessary.
creds = service_account_flow(service_account_info, SCOPES)
# Build services
SHEETS_SERVICE = build('sheets', 'v4', credentials=creds)
DRIVE_SERVICE = build('drive', 'v3', credentials=creds)
# Read data from Google Sheets into pandas DataFrames using the gsheets_to_df function.
df_palpites = gsheets_to_df(SPREADSHEETS['palpites_fg'], SHEETS_SERVICE)
df_gabarito = gsheets_to_df(SPREADSHEETS['gabarito'], SHEETS_SERVICE)
df_paises = gsheets_to_df(SPREADSHEETS['id_paises'], SHEETS_SERVICE)
df_mapa_partidas = gsheets_to_df(SPREADSHEETS['mapa_partidas_fg'], SHEETS_SERVICE)
# Normalize dataframes
df_palpites = normalize_df(df_palpites)
df_gabarito = normalize_df(df_gabarito)
df_paises = normalize_df(df_paises)
df_mapa_partidas = normalize_df(df_mapa_partidas)   
# Determine the current round by checking the count of non-empty entries in the gabarito DataFrame, which contains the correct answers for each match. 
# The minimum count across all columns gives an indication of how many rounds have been completed.
round_check = min(df_gabarito.count().to_list())
# Process the tips DataFrame to calculate predicted results and prepare it for comparison with the actual results.
df_palpites_t = tips_processing(df_palpites)
# Calculate points for each player based on their predictions and the actual results, 
# and print the resulting DataFrame with player rankings and scores.
df_palpites_final, df_points = calculate_points(df_palpites_t, df_gabarito, round_check)
# Load DataFrame to Google Drive as a CSV file using the df_to_drive_csv function

df_to_drive_csv(DRIVE_SERVICE, df_palpites_final, 'palpites.csv', PROCESSED_FOLDER_ID, overwrite=True)
if check_run_round(round_check, DRIVE_SERVICE, "1kYkENHRLwAvLiPGGamikFDzifR5KYRzh"):
    df_to_drive_csv(DRIVE_SERVICE, df_points, 'ranking_hst.csv', PROCESSED_FOLDER_ID, overwrite=False)


# df_palpites_csv = drive_csv_to_df(DRIVE_SERVICE, "1PIoax4mu5lwsWHNH4kneefyIS2I0r6H-")

df_base_table = make_base_table(df_palpites_t, df_paises)

df_to_drive_csv(DRIVE_SERVICE, df_base_table, 'tabela_base_fg.csv', PROCESSED_FOLDER_ID, overwrite=True)



df_to_gsheet(SHEETS_SERVICE, df_base_table, "1zH--PpJw0inUkOcS8y-om5Ye4W1zYRwNzHYQDYDa1BM", "tabela_base_fg", overwrite=True, include_header=True)

df_to_gsheet(SHEETS_SERVICE, df_palpites_final, "1zH--PpJw0inUkOcS8y-om5Ye4W1zYRwNzHYQDYDa1BM", "palpites", overwrite=True, include_header=True)

df_to_gsheet(SHEETS_SERVICE, df_points, "1zH--PpJw0inUkOcS8y-om5Ye4W1zYRwNzHYQDYDa1BM", "ranking_hst", overwrite=False, include_header=False)