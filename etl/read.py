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

def gsheets_to_df(sheet, sheets_service) -> pd.DataFrame:
    """
    Reads data from a Google Sheets range and returns it as a pandas DataFrame.

    Parameters
    ----------
    sheet_id : str
        The ID of the Google Sheets document.
    range : str
        The A1 notation of the values to retrieve (e.g., 'Sheet1!A1:C100').
    sheets_service : googleapiclient.discovery.Resource
        The Google Sheets API service instance.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the sheet data, where the first row is used as column headers.
        If no data is found, an empty DataFrame is returned.
    """
    # Unpack sheet configuration
    sheet_id = sheet[0]
    range = sheet[1]

    # Initialize the Google Sheets API client
    sheet = sheets_service.spreadsheets()

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
    df = pd.DataFrame(data=values[1:], columns=values[0])
    return df