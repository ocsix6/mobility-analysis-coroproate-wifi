import pandas as pd
import numpy as np
import os
import Helper
import json
import datetime
import runModelCreation


def process_transition_matrix(df):
    df = (df.iloc[~df.index.isin(['OUT']),~df.columns.isin(['IN'])])
    
    # percentage per rows, so we have the probability of beeingin A go to B
    df = (df.div(df.sum(axis=1),axis=0))*100
    # sum to each col the value of the previous ones (util for using the find_zone function)
    df = df.cumsum(axis=1)
    # drop rows with na values
    df = df.dropna()
    return df

def find_zone(df, row, valor):
    for column in df.columns:
        if valor <= df[column][row]:
            return column

def find_value_by_percent_in_vector(vector, percentage):
    for n,i in enumerate(vector):
        if percentage <= i:
            return n

def rename_csv_if_necessary(file_name):
    dir_path = Helper.project_path+Helper.config_paths['GeneralDirs']['synth_generation']+"level"+str(Helper.zone_level)+"/"+Helper.config_paths['SharedDirs']['final_data']
    file_path = dir_path+file_name
    
    if os.path.exists(file_path):
        os.rename(file_path, dir_path+Helper.actual_day+"SyntheticOld.csv")
        print(f"Already exists a file called {file_name}, renaming it to {Helper.actual_day}SyntheticOld.csv")

def create_day_path(start_hour, start_min, total_time, clusters_dfs, usr_creation_time, percent_usr_cluster, mean_time_on_zones_by_cluster):
    # total time is in hours

    print("Generating synthetic data...")

    # create output file
    create_synthetic_csv()

    # start the time
    today = datetime.date.today()
    initial_time = datetime.datetime(today.year, today.month, today.day, start_hour, start_min, 0)
    end_time = initial_time + datetime.timedelta(minutes=total_time)

    actual_time = initial_time
    user_id = 1

    # get fist user arrive time 
    actual_time = actual_time + datetime.timedelta(minutes=exponential_random(usr_creation_time))

    while actual_time <= end_time:
        # generate path of that user
        generate_user_path(clusters_dfs, actual_time, percent_usr_cluster, mean_time_on_zones_by_cluster, user_id)

        # increase time, to arrive time of next user
        actual_time = actual_time + datetime.timedelta(minutes=exponential_random(usr_creation_time))

        # increase user_id for next user
        user_id +=1
    
    order_day_path()

    print("Done!")

def generate_user_path(clusters_dfs, initial_time, percent_usr_cluster, mean_time_on_zones_by_cluster, user_id):
    # determine to wich cluster it belongs to
    random = normal_random(100)
    cluster = find_value_by_percent_in_vector(percent_usr_cluster,random)

    # pick mean time on zones of that cluster
    mean_time_on_zones_actualcluster = mean_time_on_zones_by_cluster[cluster]

    # pick and transform the transition matrix of that cluster
    transition_matrix = process_transition_matrix(clusters_dfs["cluster"+str(cluster)])

    # firsts values of actual_time and actual_zone
    actual_time = initial_time
    actual_zone = "IN"

    # add "IN" row to csv
    add_row_to_synthetic_csv(str(user_id)+","+actual_zone+","+str(actual_time)+","+str(cluster))
    
    # find first zone
    actual_zone=find_zone(transition_matrix, actual_zone, normal_random(100))

    while actual_zone!="OUT":
        # save actual zone and time info to csv
        add_row_to_synthetic_csv(str(user_id)+","+actual_zone+","+str(actual_time)+","+str(cluster))
        
        # increase actual_time (looking how much time is in the actual zone)
        actual_time = actual_time + datetime.timedelta(minutes=exponential_random(mean_time_on_zones_actualcluster[Helper.get_zone_index(actual_zone)]))

        # find next zone
        actual_zone = find_zone(transition_matrix,actual_zone,normal_random(100))
    
    # add the "OUT" row to the csv
    add_row_to_synthetic_csv(str(user_id)+","+actual_zone+","+str(actual_time)+","+str(cluster))


def create_synthetic_csv():
    dir_path = Helper.project_path+Helper.config_paths['GeneralDirs']['synth_generation']+"level"+str(Helper.zone_level)+"/"+Helper.config_paths['SharedDirs']['final_data']
    file_path = dir_path+Helper.actual_day+"Synthetic.csv"
    Helper.create_dir_if_not_exists(dir_path)
    f = open(file_path, "w")
    f.write("user_id,zone,date_time,origin_cluster\n")
    f.close()

def add_row_to_synthetic_csv(data):
    dir_path = Helper.project_path+Helper.config_paths['GeneralDirs']['synth_generation']+"level"+str(Helper.zone_level)+"/"+Helper.config_paths['SharedDirs']['final_data']
    file_path = dir_path+Helper.actual_day+"Synthetic.csv"
    f = open(file_path, "a")
    f.write(data+"\n")
    f.close()

def read_synthetic_csv(path):
    df = pd.read_csv(path,index_col=0)
    df['date_time'] = pd.to_datetime(df['date_time'])
    return df

def order_day_path():
    dir_path = Helper.project_path+Helper.config_paths['GeneralDirs']['synth_generation']+"level"+str(Helper.zone_level)+"/"+Helper.config_paths['SharedDirs']['final_data']
    
    file_path = dir_path+Helper.actual_day+"Synthetic.csv"
    
    df = read_synthetic_csv(file_path)

    df['zone'] = df['zone'].replace({'IN':'AAA'})

    df = df.sort_values(by=['date_time','zone','user_id'], ascending=True)

    df['zone'] = df['zone'].replace({'AAA':'IN'})

    df.to_csv(file_path)

def exponential_random(usr_creation_time):
    #https://numpy.org/doc/stable/reference/random/generated/numpy.random.exponential.html
    return np.random.exponential(usr_creation_time)

def normal_random(nMax):
    #https://numpy.org/doc/1.16/reference/generated/numpy.random.rand.html#numpy.random.rand
    return np.random.rand()*nMax

def prepare_needed_data():
    global file_route
    day = Helper.actual_day
    try:
        file_route = Helper.project_path+Helper.config_paths['GeneralDirs']['model_creation']+"level"+str(Helper.zone_level)+"/"+Helper.config_paths['SharedDirs']['final_data']+"/"+Helper.actual_day+".json"
        f = open(file_route,) 
        dict_data = json.load(f)
        try:
            percent_usr_cluster = dict_data[day]["PercentUsrCluster"]
            percent_usr_cluster = np.cumsum(percent_usr_cluster)
            usr_creation_time = dict_data[day]["UsrCreationTime"]
            mean_time_on_zones_by_cluster = dict_data[day]["MeanTimeOnZonesByCluster"]
            zones_names = dict_data[day]["ZonesNames"]
        except KeyError:
            print("Needed data dont found on Json data, need to run ModelCreation to obtain this data. Running...")
            runModelCreation.run_model_creation_to_specific_day(day)
            f = open(file_route,) 
            dict_data = json.load(f)
            percent_usr_cluster = dict_data[day]["PercentUsrCluster"]
            percent_usr_cluster = np.cumsum(percent_usr_cluster)
            usr_creation_time = dict_data[day]["UsrCreationTime"]
            mean_time_on_zones_by_cluster = dict_data[day]["MeanTimeOnZonesByCluster"]
            zones_names = dict_data[day]["ZonesNames"]

    except FileNotFoundError:
        print("Needed data dont found on Json data, need to run ModelCreation to obtain this data. Running...")
        runModelCreation.run_model_creation_to_specific_day(day, Helper.zone_level)
        f = open(file_route,) 
        dict_data = json.load(f)
        percent_usr_cluster = dict_data[day]["PercentUsrCluster"]
        percent_usr_cluster = np.cumsum(percent_usr_cluster)
        usr_creation_time = dict_data[day]["UsrCreationTime"]
        mean_time_on_zones_by_cluster = dict_data[day]["MeanTimeOnZonesByCluster"]
        zones_names = dict_data[day]["ZonesNames"]
    
    Helper.new_global("zones_names", zones_names)
    f.close()
    return usr_creation_time, percent_usr_cluster, mean_time_on_zones_by_cluster


def read_all_csv(route):
    clusters_dfs = {}
    for cluster in os.scandir(route):
        if cluster.path.endswith(".csv") and cluster.is_file():
            path = cluster.path
            name = cluster.name.split(".")[0]
            clusters_dfs[name] = pd.read_csv(path, index_col=0) 
    return clusters_dfs

def read_all_transition_matrices(route):
    clusters_dfs = {}
    day = route.split("/")[-1].split(".")[0]
    f = open(route,) 
    dict_data = json.load(f)

    matrices_vector = dict_data[day]["TransitionMatricesByCluster"]
    for n, cluster in enumerate(matrices_vector):
        clusters_dfs["cluster"+str(n)] = pd.DataFrame(cluster)
    
    return clusters_dfs