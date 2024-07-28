import streamlit as st
from streamlit_extras.badges import badge
from auxiliary import match_dict, matches
from change_charts import create_plot

#os.chdir('C:/Users/Aleks/OneDrive/Dokumenty/GitHub/WorldCup_App/app')

st.set_page_config(
        page_title="Euro 2024 Analytical Tool",
        #page_icon="⚽",
        page_icon='https://raw.githubusercontent.com/AKapich/StatsBomb360_App/main/logos/eurologo.ico',
    )


st.title("Euro 2024 Analytical Tool")
st.markdown("*Platform providing a handful of visualizations for every match of the last Eurp*")
st.markdown("---")

# World Cup Image
st.sidebar.image("https://raw.githubusercontent.com/AKapich/StatsBomb360_App/main/logos/EURO2024.png")

# dropdown for choosing the match
st.sidebar.title("Select Match")
selected_match = st.sidebar.selectbox("Match:", match_dict.keys(), index=9)

match_id = match_dict[selected_match]
home_team = selected_match.split(' - ')[0]
away_team = selected_match.split(' - ')[1]
competition_stage = matches[matches['match_id']==match_id].iloc[0]['competition_stage']

# choose chart type
selected_chart = st.sidebar.radio("Select Chart Type",
                                   ["Overview", "Passing Network", "Passing Sonars", "Individual Pass Map", "Team Pass Map",
                                    'Progressive Passes', 'xG Flow', "Shot Map", 'Individual Convex Hull', "Team Convex Hull",
                                    "Voronoi Diagram", "Team Expected Threat", "Pressure Heatmap"]
                                    )

match_data = matches[matches['match_id']==match_id].iloc[0]
st.write(f"### {home_team} {match_data['home_score']}:{match_data['away_score']} {away_team}")
st.markdown('---')

create_plot(selected_chart, match_id, home_team, away_team, competition_stage)

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
