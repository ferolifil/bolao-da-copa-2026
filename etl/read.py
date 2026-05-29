import pandas as pd
import io

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

    if range.startswith("palpites"):
        # Extract stage information from the range name and add it as a new column in the DataFrame.
        df['nm_fase'] = (range.split('_')[1]).split('!')[0]

    return df

def drive_csv_to_df(drive_service, file_id: str, encoding: str = "utf-8") -> pd.DataFrame:
    """
    Reads a CSV file stored on Google Drive (by file ID) and returns it as a pandas DataFrame.

    Parameters
    ----------
    drive_service : googleapiclient.discovery.Resource
        The Google Drive API service instance.
    file_id : str
        The ID of the CSV file on Google Drive.
    encoding : str, optional
        The file encoding to use (default is 'utf-8').

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the CSV data. If the file is empty or not found, returns an empty DataFrame.
    """

    try:
        # Download the file content as bytes
        file_bytes = drive_service.files().get_media(fileId=file_id).execute()
        # Read the CSV content into a DataFrame
        df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
    except Exception as e:
        print(f"Error reading CSV from Drive (file_id={file_id}): {e}")
        df = pd.DataFrame()
    return df

def check_run_round(round_check: int, drive_service: any, file_id: str, encoding: str = "utf-8") -> bool:
    """
    Checks if the current round is new by comparing the round number with the maximum round number found in the ranking_hst.csv stored on Google Drive.

    Parameters
    ----------
    round_check : int
        The current round number, determined by the count of non-empty entries in the gabarito DataFrame.
    drive_service : googleapiclient.discovery.Resource
        The Google Drive API service instance, used to read the existing ranking_hst.csv file.
    file_id : str
        The ID of the ranking_hst.csv file on Google Drive, which contains the historical rankings and points for each player.
    encoding : str, optional
        The file encoding to use when reading the CSV file (default is 'utf-8')

    Returns
    -------
    bool
        True if the file should be updated with the new round's data (i.e., if the current round number is greater than the maximum round number in the existing file),
        False if the file should not be updated.
    """
    # Read the existing ranking_hst.csv file from Google Drive into a DataFrame to check the maximum round number already recorded.
    df = drive_csv_to_df(drive_service, file_id, encoding)
    # Compare the current round number with the maximum round number in the existing DataFrame. 
    # If the current round is greater, it indicates that a new round has been completed and the file should be updated.
    if round_check > df['nr_round'].max():
        print("Gravar ranking_hst.csv")
        return True
    elif round_check < df['nr_round'].max():
        print("Round atual é menor que o máximo registrado. Verificar dados.")
        return False
    else:
        print("Arquivo já está atualizado.")
        return False