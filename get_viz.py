from statsbombpy import sb
from mplsoccer.pitch import Pitch, VerticalPitch
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patches as pat
import pandas as pd
import numpy as np
import seaborn as sns
from scipy import stats
from scipy.spatial import ConvexHull
from scipy.ndimage import gaussian_filter1d

import warnings
warnings.filterwarnings("ignore")

from auxiliary import country_colors, annotation_fix_dict, lighten_hex_color, get_players_xT, get_xT, get_starting_XI



def overview(match_id, home_team, away_team, ax):
        events = sb.events(match_id=match_id)

        def get_basic_data(team, events):
            shots = events[(events['type'] == 'Shot') & (events['team'] == team)]
            xg = round(shots['shot_statsbomb_xg'].sum(), 2)
            shot_amt = (len(shots))
            SoT = len(shots[~(shots['shot_outcome'].isin(['Blocked', 'Off T', 'Post', 'Wayward']))])
            xg_per_shot = round(xg / shot_amt, 2)
            return [xg, str(shot_amt), str(SoT), xg_per_shot]
        
        table_data = pd.DataFrame({
            home_team: get_basic_data(home_team, events),
            'Stat': ['xG', 'Shots', 'Shots on Target', 'xG per Shot'],
            away_team: get_basic_data(away_team, events)
        })

        tbl = ax.table(cellText=table_data.values, colLabels=table_data.columns, cellLoc='center', loc='center')
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(15)
        tbl.scale(1.2, 1.2)
        for key, cell in tbl.get_celld().items():
            cell.set_edgecolor('#0e1117')
            cell.set_facecolor('#0e1117')
            cell.set_text_props(color='white')
            if key[0] == 0:
                cell.set_text_props(weight='bold')


def voronoi(match_id, home_team, away_team, ax):
        df = sb.events(match_id=match_id)

        subs = df[df["substitution_outcome"].notna()]
        min_threshold = min(subs["minute"])
        sec_threshold = min(subs["second"])
        df = df[(df["minute"]<min_threshold) | ((df["minute"]==min_threshold) & (df["second"]<sec_threshold))]
        df = df[df["location"].notna()]
        df['x'], df['y'] = zip(*df['location'])
        # average location
        df = df.groupby(['player', 'team']).agg({'x': ['mean'], 'y': ['mean']})
        df.columns = ['x', 'y']
        df=df.reset_index()
        # the column responsible for voronoi division must be boolean
        df['team_id'] = df['team']==home_team

        # reverse the coords of one team
        for i in range(len(df)):
                if not (df['team_id'][i]):
                        df['x'][i] = 120-df['x'][i]
                        df['y'][i] = 80-df['y'][i]

        pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='#c7d5cc')
        pitch.draw(ax=ax)

        pitch.voronoi(df.x, df.y, df.team)
        team1,team2 = pitch.voronoi(df.x, df.y, df.team_id)

        pitch.polygon(team1, ax=ax, fc=country_colors[home_team], ec='white', lw=3, alpha=0.5)
        pitch.polygon(team2, ax=ax, fc=country_colors[away_team], ec='white', lw=3, alpha=0.5)

        # Plot players
        for i in range(len(df['x'])):
                pitch.scatter(df['x'][i],df['y'][i],ax=ax,color=country_colors[df['team'][i]])
                        
                if df['player'][i] not in annotation_fix_dict.keys():
                    annotation_text = df['player'][i].split(" ")[-1]
                else:
                    annotation_text = annotation_fix_dict[df['player'][i]].split(" ")[-1]
                        
                pitch.annotate(annotation_text, xy=(df['x'][i], df['y'][i]+2),
                                c='black', va='center', ha='center',
                                size=7.5, fontweight='bold',
                                ax=ax)
                
        ax.set_title(f'Voronoi Diagram', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def pressure_heatmap(match_id, team, ax, inverse=False):
        events = sb.events(match_id=match_id, split=True, flatten_attrs=False)
        press = events['pressures'].query(f"team=='{team}'")
        press_x, press_y = zip(*press['location'])
        if inverse:
                press_x = [120 - x for x in press_x]
                press_y = [80 - y for y in press_y]
        press_df = pd.DataFrame({'x': press_x, 'y': press_y})

        
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='white', line_zorder=2)
        pitch.draw(ax=ax)


        bin_statistic = pitch.bin_statistic(press_df.x, press_df.y, statistic='count', bins=(8, 6), normalize=False)
        pitch.heatmap(bin_statistic, edgecolor='#323b49', ax=ax, alpha=0.55,
                cmap=LinearSegmentedColormap.from_list("custom_cmap", ["#f3f9ff", country_colors[team]], N=100))

        pitch.label_heatmap(bin_statistic, color='#323b49', fontsize=12, ax=ax, ha='center', va='center',
                             fontweight='bold', family='monospace')
        if not inverse:
            pitch.annotate(text='The direction of play  ', xytext=(45, 84), xy=(85, 84), ha='center', va='center', ax=ax,
                        arrowprops=dict(facecolor='white'), fontsize=12, color='white', fontweight="bold", family="monospace")
        else:
            pitch.annotate(text='  The direction of play', xytext=(75, 84), xy=(35, 84), ha='center', va='center', ax=ax,
                        arrowprops=dict(facecolor='white'), fontsize=12, color='white', fontweight="bold", family="monospace")
            
        ax.set_title(f'{team} Pressures', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def passing_network(match_id, team, ax, inverse=False):
        passes = sb.events(match_id=match_id, split=True, flatten_attrs=False)["passes"]

        passes = sb.events(match_id=match_id, split=True, flatten_attrs=False)["passes"]
        passes = passes[passes['team']=='Spain']
        passes["recipient"] = [passes["pass"][i]["recipient"]["name"]
                        if list(passes.loc[i]["pass"].keys())[0]=="recipient"
                        else None
                        for i in passes.index]
        passes = passes[passes["recipient"].notna()]

        startingXI = get_starting_XI(match_id, team)
        passes = passes[passes['player'].isin(startingXI) & passes['recipient'].isin(startingXI)]

        passes['x'], passes['y'] = zip(*passes['location'])
        if inverse:
                passes['x'] = [120 - x for x in passes['x']]
                passes['y'] = [80 - y for y in passes['y']]
        average_location = passes.groupby('player').agg({'x': ['mean'], 'y': ['mean','count']})
        average_location.columns = ['x', 'y', 'count']

        passes_between = passes.groupby(['player', 'recipient']).id.count().reset_index()
        passes_between = passes_between.rename(columns={'id': 'pass_count'})

        # 'average_location' index is in fact 'player' column, therefore below right_index=True (we merge by it)
        passes_between = passes_between.merge(average_location, left_on="player", right_index=True)
        passes_between = passes_between.merge(average_location, left_on='recipient', right_index=True, suffixes=('','_end'))
        # setting a threshold for minimum 2 passes between players to be noted on the chart
        passes_between = passes_between.loc[(passes_between['pass_count']>1)]

        
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='#c7d5cc')
        pitch.draw(ax=ax)

        pitch.arrows(passes_between.x, passes_between.y,
                        passes_between.x_end, passes_between.y_end,
                        color='#d4d4d4',
                        alpha=pd.to_numeric(passes_between["pass_count"], downcast="float")/max(passes_between["pass_count"]),
                        ax=ax
                    )
        pitch.scatter(average_location.x, average_location.y,
                        s = pd.to_numeric(average_location["count"], downcast="float")*25,
                        color=country_colors[team], edgecolors='white',
                        ax=ax
                    )

        for _, row in average_location.iterrows():
                if row.name not in annotation_fix_dict.keys():
                    annotation_text = row.name.split(" ")[-1]
                else:
                    annotation_text = annotation_fix_dict[row.name].split(" ")[-1]
                pitch.annotate(annotation_text, xy=(row.x, row.y+3),
                                c='white', va='center', ha='center',
                                size=10, fontweight='bold',
                                ax=ax
                            )
                
        ax.set_title(f'{team} Passing Network', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def progressive_passes(match_id, team, ax, inverse=False):
        passes = sb.events(match_id=match_id, split=True, flatten_attrs=False)["passes"]
        df = passes[passes.team==team]
        
        df[['start_x', 'start_y']] = pd.DataFrame(df['location'].tolist(), index=df.index)
        df["end_x"] = [df["pass"][i]['end_location'][0] for i in df.index]
        df["end_y"] = [df["pass"][i]['end_location'][1] for i in df.index]

        if not inverse:       
            df['beginning'] = np.sqrt(np.square(120-df['start_x'])+np.square(80-df['start_y']))
            df['end'] = np.sqrt(np.square(120-df['end_x'])+np.square(80-df['end_y']))
        else:
            df['start_x'] = 120 - df['start_x']
            df['start_y'] = 80 - df['start_y']
            df['end_x'] = 120 - df['end_x']
            df['end_y'] = 80 - df['end_y']
            df['beginning'] = np.sqrt(np.square(df['start_x'])+np.square(df['start_y']))
            df['end'] = np.sqrt(np.square(df['end_x'])+np.square(df['end_y']))

        # according to definiton pass is progressive if it brings the ball closer to the goal by at least 25%
        df['progressive'] = df['end'] < 0.75*df['beginning']
        
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='#c7d5cc')
        pitch.draw(ax=ax)

        df = df[df['progressive']==True]
        df.index = range(len(df))
        pitch.lines(xstart=df["start_x"], ystart=df["start_y"], xend=df["end_x"], yend=df["end_y"],
                ax=ax, comet=True, color=country_colors[team])
        
        ax.set_title(f'{team} Progressive Passes', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def final_3rd_passes(match_id, team, ax, inverse=False):
        passes = sb.events(match_id=match_id, split=True, flatten_attrs=False)["passes"]
        df = passes[passes.team==team]
        
        df[['start_x', 'start_y']] = pd.DataFrame(df['location'].tolist(), index=df.index)
        df["end_x"] = [df["pass"][i]['end_location'][0] for i in df.index]
        df["end_y"] = [df["pass"][i]['end_location'][1] for i in df.index]

        if inverse:
            df['start_x'] = 120 - df['start_x']
            df['start_y'] = 80 - df['start_y']
            df['end_x'] = 120 - df['end_x']
            df['end_y'] = 80 - df['end_y']

        df['to_final_3rd'] = df['end_x'] > 80 if not inverse else df['end_x'] < 40
        
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='#c7d5cc')
        pitch.draw(ax=ax)

        df = df[df['to_final_3rd']==True]
        df.index = range(len(df))
        pitch.lines(xstart=df["start_x"], ystart=df["start_y"], xend=df["end_x"], yend=df["end_y"],
                ax=ax, comet=True, color=country_colors[team])
        
        ax.set_title(f'{team} Passes to Final 3rd', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def penalty_passes(match_id, team, ax, inverse=False):
        passes = sb.events(match_id=match_id, split=True, flatten_attrs=False)["passes"]
        df = passes[passes.team==team]
        
        df[['start_x', 'start_y']] = pd.DataFrame(df['location'].tolist(), index=df.index)
        df["end_x"] = [df["pass"][i]['end_location'][0] for i in df.index]
        df["end_y"] = [df["pass"][i]['end_location'][1] for i in df.index]

        if inverse:
            df['start_x'] = 120 - df['start_x']
            df['start_y'] = 80 - df['start_y']
            df['end_x'] = 120 - df['end_x']
            df['end_y'] = 80 - df['end_y']

        df['to_penalty'] = (df['end_x'].between(102, 120) & df['end_y'].between(18, 62)) if not inverse else (df['end_x'].between(0, 18) & df['end_y'].between(18, 62))
        
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='#c7d5cc')
        pitch.draw(ax=ax)

        df = df[df['to_penalty']==True]
        df.index = range(len(df))
        pitch.lines(xstart=df["start_x"], ystart=df["start_y"], xend=df["end_x"], yend=df["end_y"],
                ax=ax, comet=True, color=country_colors[team])
        
        ax.set_title(f'{team} Passes to Penalty Area', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def team_convex_hull(match_id, team, ax, inverse=False):
        events = sb.events(match_id=match_id)
        events = events[events["team"]==team]
        startingXI = get_starting_XI(match_id, team)

        events = events[events["location"].notna()]
        events['x'], events['y'] = zip(*events['location'])
        if inverse:
                events['x'] = 120 - events['x']
                events['y'] = 80 - events['y']
        
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='#c7d5cc')
        pitch.draw(ax=ax)

        colors = ['#eb4034', '#ebdb34', '#98eb34', '#34eb77', '#be9cd9', '#5797e6',
                   '#fbddad', '#de34eb', '#eb346b', '#34ebcc', '#dbd5d5']
        colordict = dict(zip(startingXI, colors))

        for player in startingXI:
                tempdf = events[events["player"]==player]
                # threshold of 0.75 sd
                tempdf = tempdf[np.abs(stats.zscore(tempdf[['x','y']])) < 0.75]
                actions =  tempdf[['x','y']].dropna().values
                
                if player not in annotation_fix_dict.keys():
                    annotation_text = player.split(" ")[-1]
                else:
                    annotation_text = annotation_fix_dict[player].split(" ")[-1]
                pitch.annotate(annotation_text, xy=(np.mean(tempdf.x), np.mean(tempdf.y)),
                                c=colordict[player], va='center', ha='center',
                                size=10, fontweight='bold',
                                ax=ax)
        
                try:
                    hull = ConvexHull(actions)
                except:
                    pass
                try:
                    for i in hull.simplices:
                        ax.plot(actions[i, 0], actions[i, 1], colordict[player])
                        ax.fill(actions[hull.vertices, 0], actions[hull.vertices, 1], c=colordict[player], alpha=0.03)
                except:
                        pass

        ax.set_title(f'{team} Action Territories', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def shot_types(match_id, home_team, away_team, ax):

        outcome_dict = {
        "Blocked":"s",
        "Goal" : "*",
        "Off T": "X",
        "Post": "P",
        "Saved":"o",
        "Wayward":"v",
        "Saved Off T":"h",
        "Saved to Post":"p"
        }

        
        pitch = VerticalPitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='#c7d5cc')
        pitch.draw(ax=ax)

        shots = sb.events(match_id=match_id, split=True, flatten_attrs=False)["shots"]

        shots[['start_x', 'start_y']] = pd.DataFrame(shots['location'].tolist(), index=shots.index)
        shots.index = range(len(shots))

        for i in range(len(shots)):
                if shots.iloc[i].team==home_team:
                        ax.scatter(shots["start_y"][i], shots["start_x"][i],
                                color=country_colors[home_team],
                                edgecolors='white',
                                marker=outcome_dict[shots["shot"][i]["outcome"]["name"]],
                                s=120)
                else:
                        # vertical pitch, therefore y and coords exchanged
                        ax.scatter(80-shots["start_y"][i], 120-shots["start_x"][i],
                                color=country_colors[away_team],
                                edgecolors='white',
                                marker=outcome_dict[shots["shot"][i]["outcome"]["name"]],
                                s=120)   

        legend_elements=[Line2D([], [], marker='s', linestyle='None', markersize=10, label='Blocked', markerfacecolor='white', markeredgecolor='black'),
                        Line2D([], [], marker='*', linestyle='None', markersize=10, label='Goal', markerfacecolor='white', markeredgecolor='black'),
                        Line2D([], [], marker='X', linestyle='None', markersize=10, label='Off Target', markerfacecolor='white', markeredgecolor='black'),
                        Line2D([], [], marker='P', linestyle='None', markersize=10, label='Post', markerfacecolor='white', markeredgecolor='black'),
                        Line2D([], [], marker='v', linestyle='None', markersize=10, label='Wayward', markerfacecolor='white', markeredgecolor='black'),
                        Line2D([], [], marker='o', linestyle='None', markersize=10, label='Saved', markerfacecolor='white', markeredgecolor='black'),
                        Line2D([], [], marker='h', linestyle='None', markersize=10, label='Saved Off Target', markerfacecolor='white', markeredgecolor='black'),
                        Line2D([], [], marker='p', linestyle='None', markersize=10, label='Saved To Post', markerfacecolor='white', markeredgecolor='black')]
        ax.legend(handles=legend_elements, loc='center', )

        ax.set_title(f'Shot Map', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def passing_sonars(match_id, team, ax, inverse=False):
        # passing sonars
        passes = sb.events(match_id=match_id, split=True, flatten_attrs=False)["passes"]
        df = passes[passes['team']==team]
        df = df[['pass', 'player']]
        df.index = range(len(df))
        df['angle'] = [df['pass'][i]['angle'] for i in range(len(df))]
        df['length'] = [df['pass'][i]['length'] for i in range(len(df))]

        # we divide into 20 bins
        df['angle_bin'] = pd.cut(df['angle'], bins=np.linspace(-np.pi,np.pi,21),
                                labels=False, include_lowest=True)

        pass_sonar = df.groupby(["player", "angle_bin"], as_index=False)
        pass_sonar = pass_sonar.agg({"length": "mean"})
        # count occurances of passes in particular bins
        counter  = df.groupby(['player', 'angle_bin']).size().to_frame(name = 'amount').reset_index()
        pass_sonar = pd.concat([pass_sonar, counter["amount"]], axis=1)

        # average location of players
        passes['x'], passes['y'] = zip(*passes['location'])
        passes = passes[passes['team']==team]
        average_location = passes.groupby('player').agg({'x': ['mean'], 'y': ['mean']})
        average_location.columns = ['x', 'y']

        if inverse:
                average_location['x'] = 120 - average_location['x']
                average_location['y'] = 80 - average_location['y']
                pass_sonar['angle_bin'] = (pass_sonar['angle_bin'] + 10) % 20

        pass_sonar = pass_sonar.merge(average_location, left_on="player", right_index=True)

        startingXI = get_starting_XI(match_id, team)

        pass_sonar = pass_sonar[pass_sonar['player'].isin(startingXI)]
        
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='#c7d5cc')
        pitch.draw(ax=ax)

        for player in startingXI:
                for _, row in pass_sonar[pass_sonar.player == player].iterrows():
                        theta_left_start = 198

                        opacity = 0.4 if row.amount < 3 else 0.77 if row.amount < 5 else 1
                        
                        theta_left = theta_left_start + (360 / 20) * (row.angle_bin)
                        theta_right = theta_left - (360 / 20)
                        
                        pass_wedge = pat.Wedge(
                        center=(row.x, row.y),
                        r=row.length*0.2,
                        theta1=theta_right,
                        theta2=theta_left,
                        facecolor=country_colors[team],
                        edgecolor="black",
                        alpha=opacity,
                        )
                        ax.add_patch(pass_wedge)

        for _, row in average_location.iterrows():
                if row.name in startingXI:
                    if row.name not in annotation_fix_dict.keys():
                        annotation_text = row.name.split(" ")[-1]
                    else:
                        annotation_text = annotation_fix_dict[row.name].split(" ")[-1]
                    pitch.annotate(annotation_text, xy=(row.x, row.y+4.5),
                            c='white', va='center', ha='center',
                            size=9, fontweight='bold',
                            ax=ax)

        ax.set_title(f'{team} Passing Sonars', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def xG_flow(match_id, home_team, away_team, ax):
        shots = sb.events(match_id=match_id, split=True, flatten_attrs=False)["shots"]
        shots.index = range(len(shots))

        shots["xG"] = [shots["shot"][i]["statsbomb_xg"] for i in range(len(shots))]
        shots["outcome"] = [shots["shot"][i]["outcome"]["name"] for i in range(len(shots))]
        shots = shots[["minute", "second", "team", "player", "xG", "outcome"]]

        a_xG = [0]
        h_xG= [0]
        a_min = [0]
        h_min = [0]

        for i in range(len(shots)):
                if shots['team'][i]==away_team:
                        a_xG.append(shots['xG'][i])
                        a_min.append(shots['minute'][i])
                if shots['team'][i]==home_team:
                        h_xG.append(shots['xG'][i])
                        h_min.append(shots['minute'][i])
                
        def cumsum(the_list):
                return [sum(the_list[:i+1]) for i in range(len(the_list))]
        
        a_xG = cumsum(a_xG)
        h_xG = cumsum(h_xG)

        # make the plot finish at the end of an axis for both teams
        if(a_min[-1]>h_min[-1]):
                h_min.append(a_min[-1])
                h_xG.append(h_xG[-1])
        elif (h_min[-1]>a_min[-1]):
                a_min.append(h_min[-1])
                a_xG.append(a_xG[-1])

        a_xG_total = round(a_xG[-1], 2)
        h_xG_total = round(h_xG[-1], 2)

        # goals
        goals = shots[shots['outcome']=='Goal']
        a_goals, h_goals = [], []
        for _, row in goals.iterrows():
            if row['player'] not in annotation_fix_dict.keys():
                annotation_text = row['player'].split(" ")[-1]
            else:
                annotation_text = annotation_fix_dict[row['player']].split(" ")[-1]
            if row['team'] == away_team:
                a_goals.append((row['minute'], a_xG[a_min.index(row['minute'])], annotation_text))
            else:
                h_goals.append((row['minute'], h_xG[h_min.index(row['minute'])], annotation_text))

        ax.axis('on')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
    

        ax.step(x=a_min, y=a_xG, color=country_colors[away_team], where='post', linewidth=4)
        ax.step(x=h_min, y=h_xG, color=country_colors[home_team], where='post', linewidth=4)
        ax.set_xticks([0,15,30,45,60,75,90,105,120])
        ax.set_xlabel('Minute',fontname='Monospace',color='white',fontsize=16)
        ax.set_ylabel('xG',fontname='Monospace',color='white',fontsize=16)

        ax.scatter([i[0] for i in a_goals], [i[1] for i in a_goals],
                   color=country_colors[away_team], zorder=10, s=250, marker='h', edgecolor='white')
        ax.scatter([i[0] for i in h_goals], [i[1] for i in h_goals],
                   color=country_colors[home_team], zorder=10, s=250, marker='h', edgecolor='white')
        for goal in a_goals:
            ax.annotate(goal[2], (goal[0], goal[1]), textcoords="offset points",
                        xytext=(0,10), ha='center', color='white', fontsize=10, fontname='Monospace')
        for goal in h_goals:
            ax.annotate(goal[2], (goal[0], goal[1]), textcoords="offset points",
                        xytext=(0,10), ha='center', color='white', fontsize=10, fontname='Monospace')
        
        # Handling Own Goals
        events = sb.events(match_id=match_id)
        for _, row in events.query('type == "Own Goal Against"').iterrows():
            color = country_colors[home_team] if row['team'] == away_team else country_colors[away_team]
            for_team = home_team if row['team'] == away_team else away_team
            y = row['minute']
            x = shots[shots['minute'] < row['minute']][shots['team']==for_team]['xG'].sum()
            ax.scatter(y, x, color=color, zorder=10, s=250, marker='h', edgecolor='white')
            ax.annotate(f'Own Goal', (y, x), textcoords="offset points",
                        xytext=(0,10), ha='center', color='white', fontsize=10, fontname='Monospace')
              

        ax.grid(ls='dotted',lw=.5,color='lightgrey',axis='y',zorder=1)

        spines = ['top','bottom','left','right']
        for x in spines:
                if x in spines:
                        ax.spines[x].set_visible(False)
                
        ax.margins(x=0)
        ax.axhline(h_xG_total, color=country_colors[home_team], linestyle='--')
        ax.axhline(a_xG_total, color=country_colors[away_team], linestyle='--')
        h_text = str(h_xG_total)+' '+home_team
        a_text = str(a_xG_total)+' '+away_team
        ax.text(5, h_xG_total+0.05, h_text, fontsize = 10, color=country_colors[home_team])
        ax.text(5, a_xG_total+0.05, a_text, fontsize = 10, color=country_colors[away_team])

        ax.set_title(f'xG Flow', fontname='Monospace', color='white', fontsize=20, fontweight='bold', pad=10)


def shot_xg(match_id, team, ax, inverse=False):
    events = sb.events(match_id=match_id)
    shots = events.query(f' type == "Shot" and team == "{team}"')
    shots['x'], shots['y'] = zip(*shots['location'])

    pitch = VerticalPitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='#c7d5cc', half=True)
    pitch.draw(ax=ax)

    color = country_colors[team]
    for _, row in shots.iterrows():
        marker = '*' if row['shot_outcome'] == 'Goal' else 'o'
        ax.scatter(row["y"], row["x"],
                color=color,
                edgecolors='white',
                marker=marker,
                s=row['shot_statsbomb_xg']*650
        )

    legend_elements=[Line2D([], [], marker='o', linestyle='None', markersize=3, label='xG = 0.2', markerfacecolor='white', markeredgecolor='black'),
                    Line2D([], [], marker='o', linestyle='None', markersize=6, label='xG = 0.4', markerfacecolor='white', markeredgecolor='black'),
                    Line2D([], [], marker='o', linestyle='None', markersize=9, label='xG = 0.6', markerfacecolor='white', markeredgecolor='black'),
                    Line2D([], [], marker='o', linestyle='None', markersize=12, label='xG = 0.8', markerfacecolor='white', markeredgecolor='black'),
                    Line2D([], [], marker='o', linestyle='None', markersize=15, label='xG = 1', markerfacecolor='white', markeredgecolor='black')]
    ax.legend(handles=legend_elements, loc='lower center')

    ax.set_title(f'{team} Shots by xG', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def pass_heatmap(match_id, team, ax, inverse=False):
    passes = sb.events(match_id=match_id, split=True, flatten_attrs=False)["passes"]
    passes = passes.query(f'team == "{team}"')
    
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='#c7d5cc')
    pitch.draw(ax=ax)

    passes['x'], passes['y'] = zip(*passes['location'])
    if inverse:
        passes['x'] = 120 - passes['x']
        passes['y'] = 80 - passes['y']

    sns.kdeplot(
            x=passes["x"],
            y=passes["y"],
            fill = True,
            shade_lowest=False,
            alpha=.6,
            n_levels=10,
            cmap = LinearSegmentedColormap.from_list('', [lighten_hex_color(country_colors[team], 0.45), country_colors[team]], N=100),
            ax=ax
        )
    ax.set_xlim(0,120)
    ax.set_ylim(80,0)

    ax.set_title(f'{team} Passes Heatmap', color='white', size=20, fontweight='bold')


def xT_scatterplot(match_id, home_team, away_team, ax):
    xtdf = get_players_xT(match_id)

    top_xT = xtdf.sort_values('total_xT', ascending=False).head(5)['player'].values
    top_pass_xT = xtdf.sort_values('pass_xT', ascending=False).head(5)['player'].values
    top_carry_xT = xtdf.sort_values('carry_xT', ascending=False).head(5)['player'].values

    ax.axis('on')
    for _, row in xtdf.iterrows():
        ax.scatter(
            x=row['pass_xT'],
            y=row['carry_xT'],
            s=100,
            color=country_colors[row['team']],
            edgecolor='white',
            linewidth=1
        )

        if row['player'] in top_pass_xT or row['player'] in top_carry_xT or row['player'] in top_xT:
            if row['player'] not in annotation_fix_dict.keys():
                annotation_text = row['player'].split(" ")[-1]
            else:
                annotation_text = annotation_fix_dict[row['player']].split(" ")[-1] 

            ax.text(
                row['pass_xT'],
                row['carry_xT']+0.08*max(xtdf['carry_xT']),
                annotation_text,
                fontname='Monospace',
                color='white',
                ha='center',
                va='center',
                fontweight='bold'
            )
        
    ax.set_xlabel('Pass xT', fontname='Monospace',color='white',fontsize=16)
    ax.set_ylabel('Carry xT', fontname='Monospace',color='white',fontsize=16)
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')

    for x in ['top','bottom','left','right']:
            if x in ['top', 'right']:
                    ax.spines[x].set_visible(False)
            else:
                    ax.spines[x].set_color('white')

    ax.set_title('Players xT', fontname='Monospace',color='white',fontsize=20, fontweight='bold')

       
def xT_heatmap(match_id, team, ax, inverse=False):
    events = sb.events(match_id=match_id)
    events = events[events['team']==team]

    xtdf = pd.concat([get_xT(events, 'Pass'), get_xT(events, 'Carry')], axis=0)
    
    if inverse:
        xtdf['start_x'] = 120 - xtdf['start_x']
        xtdf['end_x'] = 120 - xtdf['end_x']
        xtdf['start_y'] = 80 - xtdf['start_y']
        xtdf['end_y'] = 80 - xtdf['end_y']


    pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e1117', line_color='white', line_zorder=2)
    pitch.draw(ax=ax)

    bin_statistic = pitch.bin_statistic(xtdf.start_x, xtdf.start_y, values=xtdf.xT, statistic='sum', bins=(16, 12), normalize=False)
    pitch.heatmap(bin_statistic, edgecolor='None', ax=ax, alpha=0.65,
            cmap=LinearSegmentedColormap.from_list('', [lighten_hex_color(country_colors[team], 0.8), country_colors[team]], N=20))

    if not inverse:
        pitch.annotate(text='The direction of play  ', xytext=(45, 84), xy=(85, 84), ha='center', va='center', ax=ax,
                    arrowprops=dict(facecolor='white'), fontsize=12, color='white', fontweight="bold", family="monospace")
    else:
        pitch.annotate(text='  The direction of play', xytext=(75, 84), xy=(35, 84), ha='center', va='center', ax=ax,
                    arrowprops=dict(facecolor='white'), fontsize=12, color='white', fontweight="bold", family="monospace")
        
    ax.set_title(f'{team} xT Pass+Carry (Start Zones)', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)


def xT_momentum(match_id, home_team, away_team, ax):
    df = sb.events(match_id=match_id)
    home_color, away_color = country_colors[home_team], country_colors[away_team]

    xT_data = pd.concat([get_xT(events=df, type='Pass', momentum=True), get_xT(events=df, type='Carry', momentum=True)], axis=0)
    xT_data['xT_clipped'] = np.clip(xT_data['xT'], 0, 0.1)

    max_xT_per_minute = xT_data.groupby(['team', 'minute'])['xT_clipped'].max().reset_index()

    minutes = sorted(xT_data['minute'].unique())
    weighted_xT_sum = {team: [] for team in max_xT_per_minute['team'].unique()}
    momentum = []

    window_size = 4
    decay_rate = 0.25

    for current_minute in minutes:
        for team in weighted_xT_sum:
            recent_xT_values = max_xT_per_minute[(max_xT_per_minute['team'] == team) & 
                                                    (max_xT_per_minute['minute'] <= current_minute) & 
                                                    (max_xT_per_minute['minute'] > current_minute - window_size)]
            
            weights = np.exp(-decay_rate * (current_minute - recent_xT_values['minute'].values))
            weighted_sum = np.sum(weights * recent_xT_values['xT_clipped'].values)
            weighted_xT_sum[team].append(weighted_sum)

        momentum.append(weighted_xT_sum[home_team][-1] - weighted_xT_sum[away_team][-1])

    momentum_df = pd.DataFrame({
        'minute': minutes,
        'momentum': momentum
    })

    ax.axis('on')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)
    for spine in ['top', 'right', 'bottom', 'left']:
        ax.spines[spine].set_visible(False)
    ax.set_xticks([0,15,30,45,60,75,90])
    ax.margins(x=0)
    ax.set_ylim(-0.12, 0.12)

    momentum_df['smoothed_momentum'] = gaussian_filter1d(momentum_df['momentum'], sigma=1)
    ax.plot(momentum_df['minute'], momentum_df['smoothed_momentum'], color='white')

    ax.axhline(0, color='white', linestyle='--', linewidth=0.5)
    ax.fill_between(momentum_df['minute'], momentum_df['smoothed_momentum'], where=(momentum_df['smoothed_momentum'] > 0), color=home_color, alpha=0.5, interpolate=True)
    ax.fill_between(momentum_df['minute'], momentum_df['smoothed_momentum'], where=(momentum_df['smoothed_momentum'] < 0), color=away_color, alpha=0.5, interpolate=True) 

    ax.set_xlabel('Minute', color='white', fontsize=15, fontweight='bold', fontfamily='Monospace')
    ax.set_ylabel('Momentum', color='white', fontsize=15, fontweight='bold', fontfamily='Monospace')
    ax.set_title(f'xT Momentum', color='white', fontsize=20, fontweight='bold', fontfamily='Monospace', pad=-5)

    goals = df[(df['shot_outcome']=='Goal') | (df['type']=='Own Goal For')][['minute', 'team']]

    for _, row in goals.iterrows():
        ymin, ymax = (0.5, 0.9) if row['team'] == home_team else (0.1, 0.5)
        ax.axvline(row['minute'], color='white', linestyle='--', linewidth=1.2, alpha=0.8, ymin=ymin, ymax=ymax)
        ax.scatter(row['minute'], (1 if row['team'] == home_team else -1)*0.10, color='white', s=100, zorder=10, alpha=1)
        ax.text(row['minute']+0.1, (1 if row['team'] == home_team else -1)*0.11, 'Goal', fontsize=10, ha='center', va='center', fontfamily="Monospace", color='white')


viz_dict = {
        "Overview": overview,
        "Voronoi Diagram": voronoi,
        "Pressure Heatmap": pressure_heatmap,
        "Passing Network": passing_network,
        'Progressive Passes': progressive_passes,
        'Action Territories': team_convex_hull,
        "Shot Types": shot_types,
        "Passing Sonars": passing_sonars,
        "xG Flow": xG_flow,
        "Shot xG": shot_xg,
        'Pass Heatmap': pass_heatmap,
        'xT by Players': xT_scatterplot,
        'xT Heatmap': xT_heatmap,
        'Passes to Final 3rd': final_3rd_passes,
        'Passes to Penalty Area': penalty_passes,
        'xT Momentum': xT_momentum
}
