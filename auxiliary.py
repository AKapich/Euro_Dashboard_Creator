from statsbombpy import sb
import pandas as pd
import numpy as np

# Data from World Cup 2022
matches = sb.matches(competition_id=55, season_id=282)
match_dict = {home+' - '+away: match_id
                 for match_id, home, away
                 in zip(matches['match_id'], matches['home_team'], matches['away_team'])}

country_colors = {
    "Poland": "#de1a41",
    "Denmark": "#C60C30",
    "Portugal": "#006400",
    "Germany": "#000000",
    "France": "#0055A4",
    "Netherlands": "#E77E02",
    "Belgium": "#FFD700",
    "Spain": "#C60C30",
    "Croatia": "#FF0000",
    "England": "#002366",
    "Serbia": "#DC143C",
    "Switzerland": "#FF0000",
    "Scotland": '#006cb7',
    'Hungary': '#008d55',
    'Albania': '#ed1b24',
    'Italy': '#009247',
    'Slovenia': '#005aab',
    'Austria': '#ed1b24',
    'Slovakia': '#005aab',
    'Romania': '#ffde00',
    'Ukraine': '#005aab',
    'Turkey': '#ed1b24',
    'Georgia': '#fffffc',
    'Czech Republic': '#005aab'
}


def get_starting_XI(match_id, team):
    events = sb.events(match_id=match_id)
    events = events[events["team"]==team]
    players = events[pd.isna(events["player"])==False]["player"].unique()
    eleven = players[:11] # first eleven

    lineups = sb.lineups(match_id)
    lineup = lineups[team][lineups[team]['player_name'].isin(list(set(eleven)))][['player_name', 'jersey_number']].sort_values('jersey_number')
    lineup.columns = ['Player', 'Number']
    lineup.index = lineup['Number']
    return lineup['Player']


annotation_fix_dict = {
    'Lottin': 'Mbappé',
    'Aveiro': 'Ronaldo',
    'Teixeira': 'Dalot',
    'Sequeira': 'Félix',
    'Arthuer': 'Williams',
    'Mendibil': 'Simón',
    'Carvajal': 'Olmo',
    'Cascante': 'Rodri',
}
