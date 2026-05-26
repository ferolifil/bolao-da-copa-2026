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