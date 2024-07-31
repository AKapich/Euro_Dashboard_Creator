import streamlit as st
from streamlit_extras.badges import badge
from auxiliary import match_dict, matches, country_colors
from get_viz import viz_dict

import pandas as pd
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from PIL import Image


st.set_page_config(
        page_title="Create Your Own Euro 2024 Match Dashboard!",
        page_icon='https://raw.githubusercontent.com/AKapich/StatsBomb360_App/main/logos/eurologo.ico',
    )


st.title("Euro 2024 Analytical Tool")
st.markdown("*Platform enabling users to create their own match dashboards*")
st.sidebar.image("https://raw.githubusercontent.com/AKapich/StatsBomb360_App/main/logos/EURO2024.png")

# dropdown for choosing the match
st.sidebar.title("Select Match")
selected_match = st.sidebar.selectbox("Match:", match_dict.keys(), index=1)

match_id = match_dict[selected_match]
home_team = selected_match.split(' - ')[0]
away_team = selected_match.split(' - ')[1]
competition_stage = matches[matches['match_id']==match_id].iloc[0]['competition_stage']


side_charts = ["None", "Passing Network", "Passing Sonars", "Shot xG", "Pass Heatmap", "xT Heatmap", "Pressure Heatmap",  "Action Territories",
               'Progressive Passes', "Passes to Final 3rd", "Passes to Penalty Area"]

middle_charts = ["None", "Overview", 'xG Flow', "Voronoi Diagram", 'xT by Players', "Shot Types"]

match_data = matches.query('match_id == @match_id').iloc[0]
##################################################################

tab1, tab2 = st.tabs(["Creator Menu", "Dashboard Overview"])

with tab1:
    n_rows = st.slider('Number of Rows', 2, 5, 3)
    n_rows += 1
    cols = st.columns(3) 
    selected_options = [[None for _ in range(3)] for _ in range(n_rows)]

    for i in range(1, len(selected_options)):
        for j in range(len(selected_options[i])):
            with cols[j]:
                if j == 1:
                    selected_options[i][j] = st.selectbox(f'Row {i} & Column {j + 1}', middle_charts)
                else:
                    selected_options[i][j] = st.selectbox(f'Row {i} & Column {j + 1}', side_charts)
    st.markdown('---')

with tab2: 
    pass
height_ratios = [1] + [2 for _ in range(n_rows-1)]
fig_height = 10 + 5 * (n_rows - 2)
axes = [[None for _ in range(3)] for _ in range(n_rows)]


fig = plt.figure(figsize=(25, fig_height), constrained_layout=True)
fig.patch.set_facecolor('#0e1117')
gs = fig.add_gridspec(nrows=n_rows, ncols=3, height_ratios=height_ratios, width_ratios=[1, 1, 1])

for i in range(len(axes)):
    for j in range(len(axes[i])):
        axes[i][j] = fig.add_subplot(gs[i,j])
        axes[i][j].patch.set_facecolor('#0e1117') 
        axes[i][j].axis('off')


axes[0][0].imshow(Image.open(f'./federations/{home_team}.png'))
axes[0][2].imshow(Image.open(f'./federations/{away_team}.png'))

home_team_text = axes[0][1].text(0.2, 0.4, home_team, fontsize=30, ha='center', fontfamily="Monospace", fontweight='bold', color='white')
home_team_text.set_bbox(dict(facecolor=country_colors[home_team], alpha=0.5, edgecolor='white', boxstyle='round'))
away_team_text = axes[0][1].text(0.8, 0.4, away_team, fontsize=30, ha='center', fontfamily="Monospace", fontweight='bold', color='white')
away_team_text.set_bbox(dict(facecolor=country_colors[away_team], alpha=0.5, edgecolor='white', boxstyle='round'))
score_text = axes[0][1].text(
    0.5,
    0,
    f'{match_data.home_score} - {match_data.away_score}',
    fontsize=40,
    ha='center',
    fontfamily="Monospace",
    fontweight='bold',
    color='white'
)


for i in range(1, len(axes)):
    for j in range(len(axes[i])):
        if selected_options[i][j] != 'None':
            if j == 1:
                viz_dict[selected_options[i][j]](match_id, home_team, away_team, axes[i][j])
                if selected_options[i][j] == 'xG Flow':
                    axes[i][j].set_xlabel('Minute',fontname='Monospace',color='white',fontsize=16)
                    axes[i][j].set_ylabel('xG',fontname='Monospace',color='white',fontsize=16)
            elif j == 0:
                viz_dict[selected_options[i][j]](match_id, home_team, axes[i][j])
            elif j == 2:
                viz_dict[selected_options[i][j]](match_id, away_team, axes[i][j], inverse=True)

st.pyplot(fig)

##################################################################
import io
buf = io.BytesIO()
fig.savefig(buf, format='png')
buf.seek(0)

st.sidebar.download_button(
    label="Download Your Dashboard",
    data=buf,
    file_name="dashboard.png",
    mime="image/png"
)

##################################################################
st.markdown('---')
st.image('https://raw.githubusercontent.com/AKapich/WorldCup_App/main/app/sb_icon.png',
          caption='App made by Aleks Kapich. Data powered by StatsBomb', use_column_width=True)

# signature
st.sidebar.markdown('---')
col1, col2 = st.columns(2)
with col1:
    st.sidebar.markdown("App made by **Aleks Kapich**")
with col2:
    with st.sidebar:
        badge(type="twitter", name="AKapich")
        badge(type="github", name="AKapich")
        badge(type="buymeacoffee", name="akapich")
