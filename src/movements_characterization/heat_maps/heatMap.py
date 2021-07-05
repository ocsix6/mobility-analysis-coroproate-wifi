import folium
from folium.plugins import HeatMapWithTime
import pandas as pd
import numpy as np
import configparser
import os
import json

def get_project_path(file_name="README.md", actual_path=None):
    if not actual_path:
        actual_path = os.path.dirname(os.path.abspath(file_name))
    if os.path.isfile(actual_path+"/"+file_name):
        return actual_path
    else:
        return get_project_path(file_name, os.path.abspath(os.path.join(actual_path, os.pardir)))

def init():
    global project_path, config
    project_path = get_project_path()+"/"
    # Read the config file
    config = configparser.ConfigParser()
    config.read(project_path+'src/movements_characterization/configs/paths.ini')

def jsonfile_to_dict(path):
    with open(path) as json_file: 
        aux = json.load(json_file)
    return aux

def load_extra_basemaps():
    return {
        'Google Maps': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Maps',
            overlay = True,
            control = True
        ),
        'Google Satellite': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Satellite',
            overlay = True,
            control = True
        ),
        'Google Terrain': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Terrain',
            overlay = True,
            control = True
        ),
        'Google Satellite Hybrid': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Satellite',
            overlay = True,
            control = True
        ),
        'Esri Satellite': folium.TileLayer(
            tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr = 'Esri',
            name = 'Esri Satellite',
            overlay = True,
            control = True
        )
    }

def process_data_for_map(day, time_period):
    time_period = np.timedelta64(time_period, 'm')
    # time_period is the period time, in minutes, to check canges
    # load the csv (after kmeans) of the selected day
    df = pd.read_csv(project_path+config['GeneralDirs']['model_creation']+"level0/"+config['SharedDirs']['df_after_kmeans']+day+".csv",index_col=0)
    df['date_time'] = pd.to_datetime(df['date_time'])

    # sort by datetime
    df = df.sort_values(by=['date_time'],ascending=True)

    first_time = df.head(1)['date_time'].values[0]
    last_time = df.tail(1)['date_time'].values[0]

    actual_time = first_time

    n_usrs_build_list = []
    ids_out = []
    while actual_time < last_time:
        # get all the samples included between start and actual_time + time_period exept IN
        df_aux = df[(df['date_time'] <= actual_time + time_period) & (df['zone']!="IN")][["date_time","zone"]]
        # dont pick "excluded" ones
        df_aux = df_aux.iloc[~df_aux.index.isin(ids_out)]
        if not df_aux.empty:
            
            tmp_data_df = df_aux.groupby('user_id').tail(1)
            # agaf pick last sample

            n_df = tmp_data_df.groupby('zone').count()
            n_df = n_df.rename(columns={"date_time": "n"})
            n_df['date_time'] = actual_time + time_period
            n_df['zone'] = n_df.index
            # delete out rows
            n_df = n_df[n_df.zone != "OUT"]

            aux_list = n_df[["date_time","zone","n"]].values.tolist()
            for element in aux_list:
                n_usrs_build_list.append(element)

            # if its OUT "exclude" the id
            ids_out.extend(tmp_data_df.index[tmp_data_df['zone'] == 'OUT'].tolist())

        actual_time += time_period
    
    return pd.DataFrame(n_usrs_build_list, columns=["date_time","zone","n"])


def get_heat_points(df):
    coordinates = jsonfile_to_dict(project_path+"src/movements_characterization/heat_maps/coordinates.json")

    heat_data = []
    heat_index = []
    for idx, group_data in df.groupby('date_time'):

        # normalize weight values
        group_data['n'] = group_data['n'] / group_data['n'].sum() * 2

        heat_data.append([[coordinates[row['zone']][0], coordinates[row['zone']][1], row['n']] for idx, row in group_data.iterrows()])
        heat_index.append(str(idx))
    
    ## return heat points
    return HeatMapWithTime(heat_data, index=heat_index, radius=0.0005, scale_radius=True, auto_play=True)


if __name__ == '__main__':
    day = "Day1"
    time_period = 5

    init()
    
    # create map
    heatMap = folium.Map(location=[39.6397266,2.6444861],zoom_start=16)
    
    # Load custom basemaps
    basemaps = load_extra_basemaps()
    
    # Add basemap
    basemaps['Google Maps'].add_to(heatMap)
    
    # add heatPoints
    get_heat_points(process_data_for_map(day,time_period)).add_to(heatMap)
    
    # save map
    dir = project_path+"data/heat_maps"
    if not os.path.isdir(dir):
        os.mkdir(dir)
    heatMap.save(dir+"/heat_map_"+day+".html")

    print("Done!")