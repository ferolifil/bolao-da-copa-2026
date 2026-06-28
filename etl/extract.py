import pandas as pd
import io
import gspread

def gsheets_to_df_old(sheet, sheets_service) -> pd.DataFrame:
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
        df['nm_fase'] = range.split('_')[1]

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

    
def gsheets_to_df(creds: any, sheets_var: list) -> pd.DataFrame:
    """
    Reads data from a Google Sheets range and returns it as a pandas DataFrame.

    Parameters
    ----------
    creds : google.oauth2.credentials.Credentials
        The authenticated credentials to access the Google Sheets API.
    sheets_var : list
        A list containing the sheet ID and tab name.
    tab_name : str
        The name of the worksheet/tab to read from.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the sheet data, where the first row is used as column headers.
        If no data is found, an empty DataFrame is returned.
    """
    # Unpack sheet configuration
    sheet_id = sheets_var[0]
    tab_name = sheets_var[1]
    # Initialize the gspread client using the provided credentials
    client = gspread.authorize(creds)
    # Open the specified Google Sheets document and worksheet/tab.
    sheet = client.open_by_key(sheet_id)
    tab = sheet.worksheet(tab_name)
    # Fetch all records and convert them into a DataFrame.
    data = tab.get_all_records()
    df = pd.DataFrame(data)
    if tab_name.startswith("palpites"):
        # Extract stage information from the range name and add it as a new column in the DataFrame.
        df['nm_fase'] = tab_name.split('_')[1]
    
    return df

def check_run_round(round_check: int, creds: any, sheets_var: list) -> bool:
    """
    Checks if the current round is new by comparing the round number with the maximum round number found in the ranking_hst.csv stored on Google Drive.

    Parameters
    ----------
    round_check : int
        The current round number, determined by the count of non-empty entries in the gabarito DataFrame.
    creds : google.oauth2.credentials.Credentials
        The authenticated credentials to access the Google Sheets API.
    sheets_var : list
        A list containing the sheet ID and tab name for the ranking_hst tab.

    Returns
    -------
    bool
        True if the file should be updated with the new round's data (i.e., if the current round number is greater than the maximum round number in the existing file),
        False if the file should not be updated.
    """
    # Read the existing ranking_hst.csv file from Google Drive into a DataFrame to check the maximum round number already recorded.
    df = gsheets_to_df(creds, sheets_var)
    # Compare the current round number with the maximum round number in the existing DataFrame. 
    # If the current round is greater, it indicates that a new round has been completed and the file should be updated.
    if df.empty and round_check == 0:
        print("Gravar ranking_hst atualizado.")
        return True
    if round_check > df['nr_round'].max():
        print("Gravar ranking_hst atualizado.")
        return True
    elif round_check < df['nr_round'].max():
        print("Round atual é menor que o máximo registrado. Verificar dados.")
        return False
    else:
        print("Arquivo já está atualizado.")
        return False


def parse_form_tips_to_long(df: pd.DataFrame, nm_fase: str | None = None) -> pd.DataFrame:
    """
    Parse a Google Forms wide export of match predictions into a long DataFrame.

    Input example columns:
    Nome\tMatch [Home]\tMatch [Away]\tEm caso de pênaltis [Match]\t...

    Returns rows with columns:
    nm_player, nm_fase, nm_cfr, nm_time_casa, vl_time_casa, nm_time_fora, vl_time_fora, tx_resultado, tx_penaltis
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "nm_player", "nm_fase", "nm_cfr", "nm_time_casa", "vl_time_casa",
            "nm_time_fora", "vl_time_fora", "tx_resultado", "tx_penaltis",
        ])

    # detect player column
    player_col = next((c for c in df.columns if str(c).strip().lower() in {"nome", "name", "player"}), None)
    if player_col is None:
        raise ValueError("Nenhuma coluna de jogador encontrada (esperado 'Nome').")

    ignored = {player_col, "Carimbo de data/hora", "Endereço de e-mail", "Deixe uma foto sua aqui", "Campeão", "Vice", "Artilheiro"}

    candidate_cols = [c for c in df.columns if c not in ignored]

    # Build matches mapping: match_ref -> {home_col, away_col, home_name, away_name, pen_col}
    matches = {}
    for col in candidate_cols:
        s = str(col).strip()
        # penalty column
        if "pênalt" in s.lower() or "penalt" in s.lower():
            # attempt to extract match ref inside brackets
            if "[" in s and "]" in s:
                match_ref = s.split("[", 1)[1].split("]", 1)[0].strip()
            else:
                match_ref = s
            matches.setdefault(match_ref, {})["pen_col"] = col
            continue

        # expected format: 'Match Ref  [Team]'
        if "[" in s and "]" in s:
            team = s.split("[", 1)[1].split("]", 1)[0].strip()
            match_ref = s.split(" [", 1)[0].strip() if " [" in s else s.split("[", 1)[0].strip()
            m = matches.setdefault(match_ref, {})
            if "home_col" not in m:
                m["home_col"] = col
                m["home_name"] = team
            elif "away_col" not in m:
                m["away_col"] = col
                m["away_name"] = team
            else:
                # ignore extras
                pass

    rows = []
    for _, row in df.iterrows():
        player = row[player_col]
        if pd.isna(player) or str(player).strip() == "":
            continue
        for match_ref, info in matches.items():
            home_col = info.get("home_col")
            away_col = info.get("away_col")
            pen_col = info.get("pen_col")
            if not home_col or not away_col:
                continue

            home_name = info.get("home_name", "")
            away_name = info.get("away_name", "")

            home_val = row.get(home_col, "")
            away_val = row.get(away_col, "")
            pen_val = row.get(pen_col, "") if pen_col else ""

            if pd.isna(home_val):
                home_val = ""
            if pd.isna(away_val):
                away_val = ""
            if pd.isna(pen_val):
                pen_val = ""

            fase_val = nm_fase if nm_fase is not None else (row.get("nm_fase", "") if "nm_fase" in df.columns else "")

            tx_res = f"{home_name} {home_val} x {away_val} {away_name}"

            rows.append({
                "nm_player": str(player).strip(),
                "nm_fase": fase_val,
                "nm_cfr": match_ref,
                "nm_time_casa": home_name,
                "vl_time_casa": home_val,
                "nm_time_fora": away_name,
                "vl_time_fora": away_val,
                "tx_resultado": tx_res,
                "tx_penaltis": pen_val,
            })

    return pd.DataFrame(rows, columns=[
        "nm_player", "nm_fase", "nm_cfr", "nm_time_casa", "vl_time_casa",
        "nm_time_fora", "vl_time_fora", "tx_resultado", "tx_penaltis",
    ])