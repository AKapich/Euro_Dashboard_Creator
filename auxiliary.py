from statsbombpy import sb
import pandas as pd
import numpy as np
import streamlit as st

# Data from Euro 2024
matches = sb.matches(competition_id=55, season_id=282)
match_dict = {home+' - '+away: match_id
                 for match_id, home, away
                 in zip(matches['match_id'], matches['home_team'], matches['away_team'])}


@st.cache_data(ttl=600, show_spinner=False)
def fetch_match_data(match_id):
    return sb.events(match_id=match_id)

@st.cache_data(ttl=600, show_spinner=False)
def fetch_match_pass_data(match_id):
    return sb.events(match_id=match_id, split=True, flatten_attrs=False)["passes"]

@st.cache_data(ttl=600, show_spinner=False)
def fetch_match_shot_data(match_id):
    return sb.events(match_id=match_id, split=True, flatten_attrs=False)["shots"]

@st.cache_data(ttl=600, show_spinner=False)
def fetch_match_split_data(match_id):
    return sb.events(match_id=match_id, split=True, flatten_attrs=False)


country_colors = {
    "Poland": "#de1a41",
    "Denmark": "#cf1f25",
    "Portugal": "#006400",
    "Germany": "#b864c1",
    "France": "#0055A4",
    "Netherlands": "#E77E02",
    "Belgium": "#FFD700",
    "Spain": "#fd112a",
    "Croatia": "#0766af",
    "England": "#002366", 
    "Serbia": "#711e28",
    "Switzerland": "#FF0000",
    "Scotland": '#006cb7',
    'Hungary': '#008d55',
    'Albania': '#711e28',
    'Italy': '#009247',
    'Slovenia': '#005aab',
    'Austria': '#711e28',
    'Slovakia': '#ef232c',
    'Romania': '#034ea2',
    'Ukraine': '#08ade8',
    'Turkey': '#ed1b24',
    'Georgia': '#711e28',
    'Czech Republic': '#005aab'
}


def get_starting_XI(match_id, team):
    events = fetch_match_data(match_id)
    events = events[events["team"]==team]
    startingXI = [p['player']['name'] for p in events[events['type']=='Starting XI']['tactics'].values[0]['lineup']]
    early_replacements = events[events['substitution_replacement'].notna()][events['minute']<30]
    early_replacements_dict = dict(zip(early_replacements['player'], early_replacements['substitution_replacement']))
    startingXI = [p if p not in early_replacements_dict.keys() else early_replacements_dict[p] for p in startingXI]
    return startingXI


def lighten_hex_color(hex_color, percentage):
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r, g, b = int(r + (255 - r) * percentage), int(g + (255 - g) * percentage), int(b + (255 - b) * percentage)
    r, g, b = min(255, int(r)), min(255, int(g)), min(255, int(b))
    
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def darken_hex_color(hex_color, percentage):
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r, g, b = int(r * (1 - percentage)), int(g * (1 - percentage)), int(b * (1 - percentage))
    r, g, b = max(0, int(r)), max(0, int(g)), max(0, int(b))
    
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def get_players_xT(match_id):
    xT = pd.read_csv("https://raw.githubusercontent.com/AKapich/WorldCup_App/main/app/xT_Grid.csv", header=None)
    xT = np.array(xT)
    xT_rows, xT_cols = xT.shape 
    events = sb.events(match_id=match_id)

    players = events[['player', 'team']].drop_duplicates().dropna()

    def get_xT(type):
        df = events[events['type']==type]
        df['start_x'], df['start_y'] = zip(*df['location'])
        df['end_x'], df['end_y'] = zip(*df[f'{type.lower()}_end_location'])

        df[f'start_{type.lower()}_x_bin'] = pd.cut(df['start_x'], bins=xT_cols, labels=False)
        df[f'start_{type.lower()}_y_bin'] = pd.cut(df['start_y'], bins=xT_rows, labels=False)
        df[f'end_{type.lower()}_x_bin'] = pd.cut(df['end_x'], bins=xT_cols, labels=False)
        df[f'end_{type.lower()}_y_bin'] = pd.cut(df['end_x'], bins=xT_rows, labels=False)
        df['start_zone_value'] = df[[f'start_{type.lower()}_x_bin', f'start_{type.lower()}_y_bin']].apply(lambda z: xT[z[1]][z[0]], axis=1)
        df['end_zone_value'] = df[[f'end_{type.lower()}_x_bin', f'end_{type.lower()}_y_bin']].apply(lambda z: xT[z[1]][z[0]], axis=1)
        df[f'{type.lower()}_xT'] = df['end_zone_value']-df['start_zone_value']

        return df[['player', f'{type.lower()}_xT']]

    for type in ['Pass', 'Carry']:
        xT_df = get_xT(type)
        xT_df = xT_df.groupby('player').sum()
        players = pd.merge(players, xT_df, on='player', how='left')

    players = players.fillna(0)
    players['total_xT'] = players['pass_xT'] + players['carry_xT']
    players = players.sort_values('total_xT', ascending=False)

    return players


def get_xT(events, type, momentum=False):
    xT = pd.read_csv("https://raw.githubusercontent.com/AKapich/WorldCup_App/main/app/xT_Grid.csv", header=None)
    xT = np.array(xT)
    xT_rows, xT_cols = xT.shape 

    df = events[events['type']==type]
    df['start_x'], df['start_y'] = zip(*df['location'])
    df['end_x'], df['end_y'] = zip(*df[f'{type.lower()}_end_location'])

    df[f'start_x_bin'] = pd.cut(df['start_x'], bins=xT_cols, labels=False)
    df[f'start_y_bin'] = pd.cut(df['start_y'], bins=xT_rows, labels=False)
    df[f'end_x_bin'] = pd.cut(df['end_x'], bins=xT_cols, labels=False)
    df[f'end_y_bin'] = pd.cut(df['end_x'], bins=xT_rows, labels=False)
    df['start_zone_value'] = df[[f'start_x_bin', f'start_y_bin']].apply(lambda z: xT[z[1]][z[0]], axis=1)
    df['end_zone_value'] = df[[f'end_x_bin', f'end_y_bin']].apply(lambda z: xT[z[1]][z[0]], axis=1)
    df['xT'] = df['end_zone_value']-df['start_zone_value']
    
    if not momentum:
        return df[['xT', 'start_x', 'start_y', 'end_x', 'end_y', 'type']]
    else:
        return df[['xT', 'minute', 'second', 'team', 'type']]


annotation_fix_dict = {
    'Mikel Merino Zazón': 'Mikel Merino',
    'Ayoze Pérez Gutiérrez': 'Ayoze Pérez',
    'José Luis Sanmartín Mato': 'Joselu',
    'Álvaro Borja Morata Martín': 'Álvaro Morata',
    'David Raya Martin': 'David Raya',
    'Aymeric Laporte': 'Aymeric Laporte',
    'José Ignacio Fernández Iglesias': 'Nacho Fernández',
    'Daniel Carvajal Ramos': 'Dani Carvajal',
    'Fabián Ruiz Peña': 'Fabián Ruiz',
    'Mikel Oyarzabal Ugarte': 'Mikel Oyarzabal',
    'Ferrán Torres García': 'Ferrán Torres',
    'Rodrigo Hernández Cascante': 'Rodri',
    'Jesús Navas González': 'Jesús Navas',
    'Alejandro Grimaldo García': 'Alejandro Grimaldo',
    'Unai Simón Mendibil': 'Unai Simón',
    'Daniel Olmo Carvajal': 'Dani Olmo',
    'Marc Cucurella Saseta': 'Marc Cucurella',
    'Robin Aime Robert Le Normand': 'Robin Le Normand',
    'Martín Zubimendi Ibáñez': 'Martín Zubimendi',
    'Pedro González López': 'Pedri',
    'Alejandro Remiro Gargallo': 'Álex Remiro',
    'Alejandro Baena Rodríguez': 'Álex Baena',
    'Daniel Vivian Moreno': 'Dani Vivian',
    'Nicholas Williams Arthuer': 'Nico Williams',
    'Fermin Lopez Marin': 'Fermin Lopez',
    'Lamine Yamal Nasraoui Ebana': 'Lamine Yamal',

    'Ricardo Iván Rodríguez Araya': 'Ricardo Rodríguez',

    'Jorge Luiz Frello Filho': 'Jorginho',

    'Vanja Milinković Savić': 'Vanja Milinković-Savić',

    'Bernardo Mota Veiga de Carvalho e Silva': 'Bernardo Silva',
    'Bruno Miguel Borges Fernandes': 'Bruno Fernandes',
    'Rui Pedro dos Santos Patrício': 'Rui Patrício',
    'Rúben Santos Gato Alves Dias': 'Rúben Dias',
    'Cristiano Ronaldo dos Santos Aveiro': 'Cristiano Ronaldo',
    'Nélson Cabral Semedo': 'Nélson Semedo',
    'João Pedro Cavaco Cancelo': 'João Cancelo',
    'Rúben Diogo Da Silva Neves': 'Rúben Neves',
    'Diogo José Teixeira da Silva': 'Diogo Jota',
    'João Félix Sequeira': 'João Félix',
    'João Maria Lobo Alves Palhinha Gonçalves': 'João Palhinha',
    'Danilo Luís Hélio Pereira': 'Danilo Pereira',
    'José Diogo Dalot Teixeira': 'Diogo Dalot',
    'Rafael Alexandre Conceição Leão': 'Rafael Leão',
    'José Pedro Malheiro de Sá': 'José Sá',
    'Kléper Laveran Lima Ferreira': 'Pepe',
    'Pedro Lomba Neto': 'Pedro Neto',
    'Diogo Meireles Costa': 'Diogo Costa',
    'Vitor Machado Ferreira': 'Vitinha',
    'Gonçalo Matias Ramos': 'Gonçalo Ramos',
    'Francisco Fernandes Conceição': 'Francisco Conceição',
    'Matheus Luiz Nunes': 'Matheus Nunes',
    'Gonçalo Bernardo Inácio': 'Gonçalo Inácio',
    'António João Pereira Albuquerque Tavares Silva': 'António Silva',

    'Kylian Mbappé Lottin': 'Kylian Mbappé',
    'Theo Bernard François Hernández': 'Theo Hernández',

    'Vernon De Marco Morlacchi': 'Vernon De Marco',

    'Romelu Lukaku Menama': 'Romelu Lukaku',
}
