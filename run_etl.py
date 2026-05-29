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
from cfg.api_credentials import local_oauth_flow
from etl.extract import gsheets_to_df, check_run_round, drive_csv_to_df
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
df_palpites_f = tips_processing(df_palpites)
# Calculate points for each player based on their predictions and the actual results, 
# and print the resulting DataFrame with player rankings and scores.
df_points = calculate_points(df_palpites_f, df_gabarito, round_check)
# Load DataFrame to Google Drive as a CSV file using the df_to_drive_csv function
df_to_drive_csv(DRIVE_SERVICE, df_palpites_f, 'palpites.csv', PROCESSED_FOLDER_ID, overwrite=True)
if check_run_round(round_check, DRIVE_SERVICE, "1kYkENHRLwAvLiPGGamikFDzifR5KYRzh"):
    df_to_drive_csv(DRIVE_SERVICE, df_points, 'ranking_hst.csv', PROCESSED_FOLDER_ID, overwrite=False)


df_palpites_csv = drive_csv_to_df(DRIVE_SERVICE, "1PIoax4mu5lwsWHNH4kneefyIS2I0r6H-")

# def make_tips_group_mapping(df_tips: pd.DataFrame, df_countries: pd.DataFrame) -> pd.DataFrame:
#     # Only makes sense for group stage, so filter for that phase
#     df_tips = df_tips[df_tips['nm_fase'] == 'fg'].copy()
#     # Create a mapping of team names to their predicted goals and group stage results for each match

import numpy as np

def solve_by_home_away(df: pd.DataFrame, id_h_a: int) -> pd.DataFrame:
    # id_h_a: 1 for home, 0 for away
    if id_h_a == 1:
        df_2 = df.rename(columns={
            "nm_time_casa": "team",
            "nm_time_fora": "opp",
            "vl_time_casa": "gf",
            "vl_time_fora": "ga",
        })
    else:
        df_2 = df.rename(columns={
            "nm_time_fora": "team",
            "nm_time_casa": "opp",
            "vl_time_fora": "gf",
            "vl_time_casa": "ga",
        })
    # Calculate points based on the comparison of predicted results with actual results, 
    # assigning 3 points for a correct home win prediction, 1 point for a correct
    df_2["pts"] = np.select(
        [df_2["gf"] > df_2["ga"], df_2["gf"] == df_2["ga"]],
        [3, 1],
        default=0,
    )
    # Calculate the predicted result for the home team based on the predicted goals for both teams.
    df_2["v"] = (df_2["gf"] > df_2["ga"]).astype(int)
    df_2["e"] = (df_2["gf"] == df_2["ga"]).astype(int)
    df_2["d"] = (df_2["gf"] < df_2["ga"]).astype(int)
    return df_2


def make_base_table(df_tips: pd.DataFrame, df_countries: pd.DataFrame) -> pd.DataFrame:
    # Create a copy of the tips DataFrame to avoid modifying the original data.
    df = df_tips.copy()
    # Create a new column 'nm_pais' that initially takes the value of 'nm_time_casa', which represents the home team in the predictions.
    df["nm_pais"] = df["nm_time_casa"]
    # Merge the tips DataFrame with the countries DataFrame to add the country ID (id_pais) based on the country name (nm_pais).
    df = pd.merge(df, df_countries, on='nm_pais', how='left')
    df.drop(["nm_pais"], axis=1, inplace=True)
    df = df.dropna()
    df['id_pais'] = df['id_pais'].astype(int)
    # Home and away results are calculated separately to account for the different perspectives of the predictions, 
    # and then concatenated together for aggregation.
    home = solve_by_home_away(df, 1)
    away = solve_by_home_away(df, 0)
    # Concatenate home and away results into a single DataFrame for aggregation.
    team_rows = pd.concat([home, away], ignore_index=True)
    # Aggregate points, wins, draws, losses, goals for, and goals against for each player, group, and team.
    df = (
        team_rows
        .groupby(["nm_player", "nm_grpo", "team"], as_index=False)
        .agg(
            pts=("pts", "sum"),
            jogos=("team", "size"),
            v=("v", "sum"),
            e=("e", "sum"),
            d=("d", "sum"),
            gp=("gf", "sum"),
            gc=("ga", "sum"),
        )
    )
    # Calculate goal difference (sg) as goals for (gp) minus goals against (gc).
    df["sg"] = df["gp"] - df["gc"]
    return df, team_rows


df_tabela_base, team_rows = make_base_table(df_palpites_csv, df_paises)

df_tabela_base['rk'] = df_tabela_base.groupby(['nm_player','nm_grpo'])['pts'].rank(method='max', ascending=False).astype(int)

# pontos por confronto direto
h2h = (
    team_rows
    .groupby(["nm_player", "nm_grpo", "team", "opp", "gf", "ga"], as_index=False)["pts"]
    .sum()
)

tot = df_tabela_base[["nm_player", "nm_grpo", "team", "pts"]].rename(columns={"pts": "total_pts"})

h2h_2 = h2h.merge(tot, on=["nm_player", "nm_grpo", "team"])

h2h_3 = h2h_2.merge(
    tot.rename(columns={"team": "opp", "total_pts": "opp_total_pts"}),
    on=["nm_player", "nm_grpo", "opp"]
)

# mantém só jogos entre equipes com o mesmo total de pontos
h2h_tied = h2h_3[h2h_3["total_pts"] == h2h_3["opp_total_pts"]]

h2h_pts = (
    h2h_tied
    .groupby(["nm_player", "nm_grpo", "team"], as_index=False)[["pts", "gf", "ga"]]
    .sum()
    .rename(columns={"pts": "h2h_pts", "gf": "h2h_gf", "ga": "h2h_ga"})
)

h2h_pts["h2h_sg"] = h2h_pts["h2h_gf"] - h2h_pts["h2h_ga"]


h2h_pts = h2h_pts.assign(
    tie_key=list(zip(h2h_pts.h2h_pts, h2h_pts.h2h_sg, h2h_pts.h2h_gf))
)

h2h_pts["rk2"] = (
    h2h_pts
    .groupby(["nm_player", "nm_grpo"])["tie_key"]
    .rank(method="dense", ascending=False)
    .astype(int)
)

h2h_pts = h2h_pts.drop(columns=["tie_key", "h2h_sg", "h2h_gf", "h2h_ga", "h2h_pts"])

df_tabela_base_2 = df_tabela_base.merge(h2h_pts, on=["nm_player", "nm_grpo", "team"], how="left").fillna(0)

df_tabela_base_3 = (
    df_tabela_base_2
        .merge(
            df_paises.drop(columns=["id_pais", "nm_grpo"]).rename(columns={"nm_pais": "team"}), 
            on="team", 
            how="left"
        )
    )

df_tabela_base_3 = df_tabela_base_3.assign(
    tie_key=list(zip(
        df_tabela_base_3["rk"],
        df_tabela_base_3["rk2"],
        df_tabela_base_3["sg"],
        df_tabela_base_3["gp"],
        df_tabela_base_3["nm_pais_ajst"],
    ))
)

df_tabela_base_3["pos"] = (
    df_tabela_base_3
    .groupby(["nm_player", "nm_grpo"])["tie_key"]
    .rank(method="dense", ascending=True)
    .astype(int)
)

df_tabela_base_3 = df_tabela_base_3.drop(columns=["tie_key", "rk", "rk2", "nm_pais_ajst"])

print(df_tabela_base_3[df_tabela_base_3['nm_player'] == 'ferolifil'].sort_values(['nm_grpo','pos'], ascending=[True, True]))


