import pandas as pd
import numpy as np
from unidecode import unidecode

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
        df_tips.melt(id_vars=["Nome","nm_fase"], var_name="col_jogo", value_name="gols")
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
            index=["Nome","nm_cfr","nm_time_casa","nm_time_fora","nm_fase"],
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
    df_tips_gs_final = df_tips_gs_pivot_unpivot[['Nome','nm_fase','nm_cfr','nm_time_casa','vl_time_casa','nm_time_fora', 'vl_time_fora','result_ref_casa']]
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
    df_merged = df_tips.merge(df_results, left_on=['nm_cfr','nm_fase'], right_on=['nm_cfr','nm_fase'], how='left')
    # Calculate points based on the comparison of predicted results with actual results, 
    # assigning 3 points for a correct home win prediction, 1 point for a correct draw prediction, 
    # and 0 points for an incorrect prediction or if the game has not been played yet.
    df_merged["vl_pontuacao"] = np.select(
        [
            df_merged["result_ref_casa_y"].isna(),  # game not played or missing data
            ((df_merged["vl_time_casa_x"] == df_merged["vl_time_casa_y"]) & (df_merged["vl_time_fora_x"] == df_merged["vl_time_fora_y"])).fillna(False),   # home team win
            (df_merged["result_ref_casa_x"] == df_merged["result_ref_casa_y"]).fillna(False),  # draw
        ],
        [None, 3, 1],  # values for each condition: empty string for missing data, 3 for home win, 1 for draw
        default=0  # away team win
    )
    # Group by player and sum points to get total score for each player, then rank players based on their scores.
    df_merged_2 = df_merged.copy()
    df_merged_2['vl_pontuacao'] = df_merged_2['vl_pontuacao'].fillna(0).astype(int)
    df_points = (
        df_merged_2
            .groupby(['nm_player','nm_fase'], as_index=False)['vl_pontuacao'].sum()
            .sort_values(by='vl_pontuacao', ascending=False)
    )
    # Assign ranks to players based on their total points, using dense ranking for ties and also a first-come-first-served ranking for tie-breaking.
    df_points['nr_rank'] = df_points['vl_pontuacao'].rank(method='dense', ascending=False).astype(int)
    df_points['nr_rank_2'] = df_points['vl_pontuacao'].rank(method='first', ascending=False).astype(int)
    # Add the current round number and timestamp of the last update to the DataFrame for tracking purposes.
    df_points['nr_round'] = round_check
    df_points['ts_atl'] = pd.Timestamp.now(tz='America/Sao_Paulo')

    df_tips_final = df_merged[['nm_player','nm_fase','nm_cfr','nm_time_casa_x', 'vl_time_casa_x', 'nm_time_fora_x', 'vl_time_fora_x', 'vl_pontuacao']]
    df_tips_final = df_tips_final.rename(columns={"nm_time_casa_x": "nm_time_casa", "nm_time_fora_x": "nm_time_fora", "vl_time_fora_x": "vl_time_fora", "vl_time_casa_x": "vl_time_casa"})
    df_tips_final['tx_resultado'] = df_tips_final['nm_time_casa'] + " " + df_tips_final['vl_time_casa'].astype(str) + " x " + df_tips_final['vl_time_fora'].astype(str) + " " + df_tips_final['nm_time_fora']

    return df_tips_final, df_points


def solve_by_home_away(df: pd.DataFrame, id_h_a: int) -> pd.DataFrame:
    """
    Convert prediction rows into a home/away perspective and calculate match points.

    This function renames the prediction columns so that the selected side becomes the team, the
    opposite side becomes the opponent, and the corresponding goals for/against are aligned
    accordingly. It then computes match points and result indicators for each row.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing match predictions with columns for home/away team names and goals.
    id_h_a : int
        Indicator of perspective: 1 for home team perspective, 0 for away team perspective.

    Returns
    -------
    pandas.DataFrame
        Transformed DataFrame with columns [team, opp, gf, ga, pts, v, e, d].
    """
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
    # Calculate points based on the comparison of predicted results with actual results.
    df_2["pts"] = np.select(
        [df_2["gf"] > df_2["ga"], df_2["gf"] == df_2["ga"]],
        [3, 1],
        default=0,
    )
    df_2["v"] = (df_2["gf"] > df_2["ga"]).astype(int)
    df_2["e"] = (df_2["gf"] == df_2["ga"]).astype(int)
    df_2["d"] = (df_2["gf"] < df_2["ga"]).astype(int)
    return df_2


def solve_ties(df_tabela_base: pd.DataFrame, team_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Resolve point ties using head-to-head criteria within each player and group.

    This function computes head-to-head points, goals scored, and goals conceded for teams
    that are tied on total points. It then applies tie-breaking rules using the following
    order: head-to-head points, head-to-head goal difference, and head-to-head goals scored.

    Parameters
    ----------
    df_tabela_base : pandas.DataFrame
        Aggregated table containing total points for each team within each player and group.
    team_rows : pandas.DataFrame
        Detailed row-level home/away results for each team and match.

    Returns
    -------
    pandas.DataFrame
        Tie-breaker DataFrame with columns ['nm_player', 'nm_grpo', 'team', 'rk2'] that can be merged
        back into the main standings table.
    """
    # To solve ties in points, we need to look at the head-to-head results between the tied teams. 
    # This involves calculating points, goal difference, and goals scored in matches between the tied teams, and then ranking them accordingly.

    # First, we calculate the head-to-head points, goals for, and goals against for each player, 
    # group, and team by merging the team_rows DataFrame with itself to compare each team's performance against its opponents.
    h2h = (
        team_rows
        .groupby(["nm_player", "nm_grpo", "team", "opp", "gf", "ga"], as_index=False)["pts"]
        .sum()
    )
    # We also need to merge the total points for each team to compare them against their opponents in the head-to-head analysis.
    tot = df_tabela_base[["nm_player", "nm_grpo", "team", "pts"]].rename(columns={"pts": "total_pts"})
    h2h = h2h.merge(tot, on=["nm_player", "nm_grpo", "team"])
    h2h = h2h.merge(
        tot.rename(columns={"team": "opp", "total_pts": "opp_total_pts"}),
        on=["nm_player", "nm_grpo", "opp"]
    )
    # Filter for tied teams to calculate their head-to-head points, goal difference, and goals scored for tie-breaking.
    h2h_tied = h2h[h2h["total_pts"] == h2h["opp_total_pts"]]
    h2h_pts = (
        h2h_tied
        .groupby(["nm_player", "nm_grpo", "team"], as_index=False)[["pts", "gf", "ga"]]
        .sum()
        .rename(columns={"pts": "h2h_pts", "gf": "h2h_gf", "ga": "h2h_ga"})
    )
    h2h_pts["h2h_sg"] = h2h_pts["h2h_gf"] - h2h_pts["h2h_ga"]
    # To break ties, we create a composite key that includes head-to-head points, head-to-head goal difference, and head-to-head goals scored.
    # Those are the standard tie-breaking criteria in FWC, applied in order to rank teams that are tied on points.
    h2h_pts = h2h_pts.assign(
        tie_key=list(zip(h2h_pts.h2h_pts, h2h_pts.h2h_sg, h2h_pts.h2h_gf))
    )
    # Rank teams based on the tie-breaking criteria, with higher head-to-head points, 
    # then goal difference, then goals scored leading to a better rank.
    h2h_pts["rk2"] = (
        h2h_pts
        .groupby(["nm_player", "nm_grpo"])["tie_key"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )
    return h2h_pts.drop(columns=["tie_key", "h2h_sg", "h2h_gf", "h2h_ga", "h2h_pts"])


def make_base_table(df_tips: pd.DataFrame, df_countries: pd.DataFrame) -> pd.DataFrame:
    """
    Build the base standings table from player tips and country lookup data.

    This function merges the normalized tip data with country metadata, computes both home and away
    results, aggregates team statistics, calculates goal difference, and applies tie-breaking logic
    to determine final positions within each player group.

    Parameters
    ----------
    df_tips : pandas.DataFrame
        Normalized DataFrame of player predictions with team and goal columns.
    df_countries : pandas.DataFrame
        DataFrame containing country names and their corresponding IDs.

    Returns
    -------
    pandas.DataFrame
        Base standings table with team-level statistics and final group positions.
    """
    # Create a copy of the tips DataFrame to avoid modifying the original data.
    df = df_tips.copy()
    df = df[df["nm_fase"] == "fg"]
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
    df['rk'] = df.groupby(['nm_player','nm_grpo'])['pts'].rank(method='max', ascending=False).astype(int)
    # To solve ties in points, we need to look at the head-to-head results between the tied teams. 
    # This involves calculating points, goal difference, and goals scored in matches between the tied teams
    df_ties = solve_ties(df, team_rows)
    # Merge the tie-breaking information back into the main DataFrame to adjust the rankings 
    # based on head-to-head criteria, and prepare for final ranking.    
    df = df.merge(df_ties, on=["nm_player", "nm_grpo", "team"], how="left").fillna(0)
    # Upper case and remove accents from team names to ensure consistent formatting for 
    # alphabetical ordering (least important criteria).
    df['nm_pais_ajst'] = df['team'].apply(lambda x: unidecode(x).upper())
    # Create a composite key for tie-breaking that includes the original rank, the head-to-head rank, and the adjusted team name for alphabetical ordering.
    df = df.assign(
        tie_key=list(zip(
            df["rk"],
            df["rk2"],
            -df["sg"],  # higher goal difference should be better
            -df["gp"],  # higher goals scored should be better
            df["nm_pais_ajst"],
        ))
    )
    # Rank finally.
    df["pos"] = (
        df
        .groupby(["nm_player", "nm_grpo"])["tie_key"]
        .rank(method="dense", ascending=True)
        .astype(int)
    )
    # Drop intermediate columns used for tie-breaking and sorting, and return the final DataFrame sorted by group and position.
    return df.drop(columns=["tie_key", "rk", "rk2", "nm_pais_ajst"]).sort_values(['nm_player','nm_grpo','pos'], ascending=[True,True,True])

def make_ranking_final(df_ranking_hst: pd.DataFrame, round_check: int) -> pd.DataFrame:
    """
    Calculate final ranking with rank changes between consecutive rounds.

    This function compares player rankings between the previous round and the current round,
    calculating rank differences and movements. For the first round, it returns the ranking as-is.
    For subsequent rounds, it merges the previous round ranking with the current round ranking,
    calculates the rank gap, and creates a formatted text representation of the rank movement
    (improvement, decline, or no change).

    Parameters
    ----------
    df_ranking_hst : pandas.DataFrame
        Historical ranking DataFrame containing rankings from multiple rounds with columns
        including 'nm_player', 'nm_fase', 'vl_pontuacao', 'nr_rank', 'nr_rank_2', 'nr_round',
        and 'ts_atl'.
    round_check : int
        The current round number being evaluated.

    Returns
    -------
    pandas.DataFrame
        Final ranking DataFrame with columns ['nm_player', 'nm_fase', 'vl_pontuacao', 'nr_rank',
        'nr_rank_2', 'nr_round', 'rk_gap', 'tx_gap', 'ts_atl']. The 'rk_gap' column contains
        the numeric rank difference (positive = improved rank, negative = declined rank),
        and 'tx_gap' contains the formatted text representation of the movement.
    """
    # Create a copy of the historical ranking DataFrame to avoid modifying the original data.
    df = df_ranking_hst.copy()
    # If the DataFrame is empty, return it as-is. If the current round is greater than 1, 
    # calculate rank changes by merging the previous round's ranking with the current round's ranking.
    if df.empty:
        return df
    elif round_check > 0:
        # Filter the DataFrame to get the previous round's ranking and the current round's ranking, then merge them on player name and phase.
        round_prev = df[df['nr_round'] != round_check]['nr_round'].max()
        df_1 = df[df['nr_round'] == round_prev]
        df_2 = df[df['nr_round'] == round_check]

        df_merged = pd.merge(df_1, df_2, on=['nm_player','nm_fase'], how='outer', suffixes=('_prev', '_curr'))
        df_merged['rk_gap'] = df_merged['nr_rank_prev'].fillna(0).astype(int) - df_merged['nr_rank_curr'].fillna(0).astype(int)

        df_merged["tx_gap"] = np.select(
            [
            df_merged['rk_gap'] > 0,
            df_merged['rk_gap'] < 0
        ],
        [
            "+" + df_merged['rk_gap'].astype(str),
            df_merged['rk_gap'].astype(str)
        ],
        default="-"
        )
        # Rename columns to have consistent names for the current round and select the final columns for the ranking table.
        df_merged = df_merged.rename(columns={'nr_rank_curr': 'nr_rank', 'vl_pontuacao_curr': 'vl_pontuacao','nr_rank_2_curr': 'nr_rank_2','nr_round_curr': 'nr_round','ts_atl_curr': 'ts_atl'})
        df_merged = df_merged[['nm_player','nm_fase','vl_pontuacao','nr_rank','nr_rank_2','nr_round','rk_gap','tx_gap','ts_atl']]
    else:
        df_merged = df
        df_merged['rk_gap'] = 0
        df_merged['tx_gap'] = "-"
        return df_merged.sort_values(by=['nr_rank','nm_player'], ascending=[True,True])