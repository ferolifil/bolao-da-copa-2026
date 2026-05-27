import pandas as pd
import numpy as np

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a pandas DataFrame by standardizing missing values and converting value columns to integer type.

    This function performs two main operations:
    1. Replaces all empty string ('') entries in the DataFrame with np.nan, ensuring missing values are properly recognized.
    2. Converts all columns whose names start with "vl_" to pandas' nullable integer type (Int64), allowing for integer data with missing values (NaN).

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to normalize. The DataFrame is modified in place.

    Returns
    -------
    pandas.DataFrame
        The normalized DataFrame, with empty strings replaced by NaN and all "vl_" columns converted to Int64.
    """
    df.replace('', np.nan, inplace=True)

    for col in df.columns:
        if col.startswith("vl_"):
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    return df

def tips_processing(df_tips: pd.DataFrame) -> pd.DataFrame:
    """
    Processes the players' tips DataFrame, transforming it from wide to long format, extracting match information,
    organizing tips by home and away teams, and normalizing the data for further analysis.

    Steps performed:
    1. Removes unnecessary columns (timestamp, photo, champion, runner-up, top scorer).
    2. Transforms the DataFrame from wide to long format (melt), making tip analysis easier.
    3. Extracts team names and match reference from the column name.
    4. Identifies whether the tip is for the home or away team.
    5. Unpivots to separate goal tips into distinct columns (home/away).
    6. Calculates the predicted result (win, draw, loss) for the home team.
    7. Renames and selects the final columns for analysis.
    8. Normalizes the final DataFrame (replaces '' with NaN and converts "vl_" columns to Int64).

    Parameters
    ----------
    df_tips : pandas.DataFrame
        Original DataFrame of players' tips, extracted from Google Sheets.

    Returns
    -------
    pandas.DataFrame
        Processed and normalized DataFrame, ready for analysis.
    """
    df_tips = df_tips.drop(columns=["Carimbo de data/hora","Deixe uma foto sua aqui", "Campeão", "Vice", "Artilheiro"])

    df_tips_gs_pivot = (
        df_tips.melt(id_vars=["Nome"], var_name="col_jogo", value_name="gols")
        .dropna(subset=["gols"])
    )

    # Extract match reference and team names from the column name using regular expressions.
    df_tips_gs_pivot["nm_cfr"] = df_tips_gs_pivot["col_jogo"].str.extract(r"^(.*) \[")[0].str.strip()
    df_tips_gs_pivot["nm_time_palpite"] = df_tips_gs_pivot["col_jogo"].str.extract(r"\[(.*)\]")[0].str.strip()
    parts = df_tips_gs_pivot["col_jogo"].str.extract(r"^(.*?) x (.*?) \[")
    df_tips_gs_pivot["nm_time_casa"] = parts[0].str.strip()
    df_tips_gs_pivot["nm_time_fora"] = parts[1].str.strip()

    # Identifies whether the tip is for the home team or the away team by comparing the predicted team name with the home team name.
    df_tips_gs_pivot["side"] = df_tips_gs_pivot.apply(
        lambda r: "vl_time_casa" if r["nm_time_palpite"] == str(r["nm_time_casa"]) else "vl_time_fora",
        axis=1,
    )

    # Unpivot to separate home and away team tips into distinct columns, using a pivot table.
    df_tips_gs_pivot_unpivot = (
        df_tips_gs_pivot.pivot_table(
            index=["Nome","nm_cfr","nm_time_casa","nm_time_fora"],
            columns="side",
            values="gols",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    # Calcuate the predicted result for the home team based on the predicted goals for both teams.
    df_tips_gs_pivot_unpivot["result_ref_casa"] = np.select(
        [
            df_tips_gs_pivot_unpivot["vl_time_casa"] > df_tips_gs_pivot_unpivot["vl_time_fora"],
            df_tips_gs_pivot_unpivot["vl_time_casa"] == df_tips_gs_pivot_unpivot["vl_time_fora"],
        ],
        ["V", "E"],
        default="D"
    )

    # Selects
    df_tips_gs_final = df_tips_gs_pivot_unpivot[['Nome','nm_cfr','nm_time_casa','vl_time_casa','nm_time_fora', 'vl_time_fora','result_ref_casa']]
    df_tips_gs_final = df_tips_gs_final.rename(columns={'Nome': 'nm_player'})

    return normalize_df(df_tips_gs_final)

def calculate_points(df_tips: pd.DataFrame, df_results: pd.DataFrame, round_check: int) -> pd.DataFrame:
    """
    Calculates the score and ranking for each player based on their predictions and the actual match results.

    This function merges the tips DataFrame with the results DataFrame, compares predictions with actual outcomes,
    assigns points according to the prediction accuracy, and ranks the players. It also adds the current round and
    a timestamp for tracking.

    Parameters
    ----------
    df_tips : pandas.DataFrame
        DataFrame containing players' predictions, processed and normalized.
    df_results : pandas.DataFrame
        DataFrame containing the actual results for each match, processed and normalized.
    round_check : int
        The current round number, used for tracking.

    Returns
    -------
    pandas.DataFrame
        DataFrame with player names, total points, rankings, round number, and last update timestamp.
    """
    # Calculate the actual result for the home team based on the actual goals for both teams, 
    # assigning "V" for home win, "E" for draw, "D" for away win, and an empty string for games that have not been played.
    df_results["result_ref_casa"] = np.select(
        [
            (df_results["vl_time_casa"].isna()) | (df_results["vl_time_fora"].isna()),  # game not played or missing data
            (df_results["vl_time_casa"] > df_results["vl_time_fora"]).fillna(False),   # home team win
            (df_results["vl_time_casa"] == df_results["vl_time_fora"]).fillna(False),  # draw
        ],
        ["", "V", "E"],  # values for each condition: empty string for missing data, "V" for home win, "E" for draw
        default="D"  # away team win
    )
    # Normalizes the results DataFrame to ensure consistent formatting and data types.
    df_results = normalize_df(df_results)
    # Merge tips with gabarito to compare predictions with actual results
    df_merged = df_tips.merge(df_results, left_on='nm_cfr', right_on='nm_cfr', how='left')
    # Calculate points based on the comparison of predicted results with actual results, 
    # assigning 3 points for a correct home win prediction, 1 point for a correct draw prediction, 
    # and 0 points for an incorrect prediction or if the game has not been played yet.
    df_merged["vl_pontucao"] = np.select(
        [
            df_merged["result_ref_casa_y"].isna(),  # game not played or missing data
            ((df_merged["vl_time_casa_x"] == df_merged["vl_time_casa_y"]) & (df_merged["vl_time_fora_x"] == df_merged["vl_time_fora_y"])).fillna(False),   # home team win
            (df_merged["result_ref_casa_x"] == df_merged["result_ref_casa_y"]).fillna(False),  # draw
        ],
        [0, 3, 1],  # values for each condition: empty string for missing data, 3 for home win, 1 for draw
        default=0  # away team win
    )
    # Group by player and sum points to get total score for each player, then rank players based on their scores.
    df_points = (
        df_merged
            .groupby('nm_player', as_index=False)['vl_pontucao'].sum()
            .sort_values(by='vl_pontucao', ascending=False)
    )
    # Assign ranks to players based on their total points, using dense ranking for ties and also a first-come-first-served ranking for tie-breaking.
    df_points['nr_rank'] = df_points['vl_pontucao'].rank(method='dense', ascending=False).astype(int)
    df_points['nr_rank_2'] = df_points['vl_pontucao'].rank(method='first', ascending=False).astype(int)
    # Add the current round number and timestamp of the last update to the DataFrame for tracking purposes.
    df_points['nr_round'] = round_check
    df_points['ts_atl'] = pd.Timestamp.now(tz='America/Sao_Paulo')

    return df_points