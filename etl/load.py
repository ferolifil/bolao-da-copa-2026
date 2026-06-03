import pandas as pd
from googleapiclient.http import MediaIoBaseUpload
import io

def df_to_drive_csv(drive_service, df, filename, folder_id=None, overwrite=False) -> str:
    """
    Save a pandas DataFrame to Google Drive as a CSV file.
    If a file with the same name already exists in the target folder, it can either be overwritten or appended to, based on the 'overwrite' parameter.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to save.
    filename : str
        The name to use for the file in Google Drive, including the .csv extension.
    folder_id : str, optional
        The Google Drive folder ID where the file should be saved.
        If omitted, the file is saved to the authenticated user's default Drive root.
    overwrite : bool, default True
        If True, overwrite an existing file with the same name in the selected folder.
        If False, create a new file instead.

    Returns
    -------
    str
        The ID of the created or updated file in Google Drive.
    """
    csv_string = df.to_csv(index=False)

    # Build the metadata for the new Drive file.
    file_metadata = {'name': filename}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    # Upload the CSV content as an in-memory bytes stream.
    media = MediaIoBaseUpload(
        io.BytesIO(csv_string.encode('utf-8')),
        mimetype='text/csv'
    )

    # Search for an existing file with the same name in the target folder.
    query = f"name = '{filename.replace("'", "\\'")}' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    else:
        query += " and 'root' in parents"

    response = drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        pageSize=1
    ).execute()

    files = response.get('files', [])
    if files:
        file_id = files[0]['id']
        if overwrite:
            # Sobrescreve o arquivo existente normalmente
            updated_file = drive_service.files().update(
                fileId=file_id,
                media_body=media,
                fields='id'
            ).execute()
            return updated_file.get('id')
        else:
            # Faz append dos dados ao arquivo existente
            # Baixa o arquivo existente
            existing_file = drive_service.files().get_media(fileId=file_id).execute()
            existing_df = pd.read_csv(io.BytesIO(existing_file))
            # Concatena os DataFrames
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            # Salva o DataFrame combinado como CSV
            combined_csv = combined_df.to_csv(index=False)
            combined_media = MediaIoBaseUpload(
                io.BytesIO(combined_csv.encode('utf-8')),
                mimetype='text/csv'
            )
            updated_file = drive_service.files().update(
                fileId=file_id,
                media_body=combined_media,
                fields='id'
            ).execute()
            return updated_file.get('id')

    # Se não existe arquivo, cria normalmente
    created_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    return created_file.get('id')


def df_to_gsheet(sheets_service, df, spreadsheet_id, sheet_name, overwrite=False, include_header=True) -> dict:
    """
    Save a pandas DataFrame into a Google Sheets worksheet.

    If overwrite is True, the function replaces the contents of the target sheet range with the DataFrame.
    If overwrite is False, the function appends the DataFrame rows to the end of the worksheet.

    Parameters
    ----------
    sheets_service : googleapiclient.discovery.Resource
        The Google Sheets API service instance.
    df : pandas.DataFrame
        The DataFrame to save.
    spreadsheet_id : str
        The ID of the Google Sheets document.
    sheet_name : str
        The name of the worksheet/tab where the data should be written.
    overwrite : bool, default False
        If True, overwrite the existing data in the sheet. If False, append rows to the end.
    include_header : bool, default True
        Whether to include the DataFrame header row in the written values. For append mode,
        set this to False if the sheet already has a header row.

    Returns
    -------
    dict
        The API response from the Sheets insert/update operation.
    """
    values = []
    if include_header:
        values.append(list(df.columns))

    if not df.empty:
        data_rows = df.fillna('').astype(str).values.tolist()
        values.extend(data_rows)

    body = {'values': values}

    if overwrite:
        range_name = f"{sheet_name}!A1"
        response = sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
    else:
        response = sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

    return response