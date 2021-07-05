import matplotlib.pyplot as plt
import UsersBuilding
import Helper
import pandas as pd
import json
import sklearn
import math
from collections import defaultdict


def run_validation_to_specific_day(day_name, zone_level):
    Helper.init()
    dir_raw_data = Helper.project_path+Helper.config_paths['GeneralDirs']['synth_generation']+"level"+str(zone_level)+"/"+Helper.config_paths['SharedDirs']['final_data']
    Helper.new_global("validation",True)
    name = day_name+"Synthetic"
    path = dir_raw_data+name+".csv"
    Helper.new_global("zone_level", zone_level)
    run_validation(path, name, zone_level)
    Helper.new_global("validation",False)


def prepare_data(path):
    zones_info = Helper.read_json_file(Helper.project_path+Helper.config_paths['GeneralDirs']['info_zones']+"zonesLevel"+str(Helper.zone_level)+".json")
    # set zones_names as a global var
    Helper.new_global("zones_names", list(zones_info.keys()))

    df = pd.read_csv(path,index_col=0)
    df['date_time'] = pd.to_datetime(df['date_time'])

    df['zone'] = df['zone'].replace({'IN':'AAA'})
    df['zone'] = df['zone'].replace({'OUT':'ZZZ'})

    df = df.sort_values(by=['user_id', 'date_time','zone'], ascending=True)

    df['zone'] = df['zone'].replace({'AAA':'IN'})
    df['zone'] = df['zone'].replace({'ZZZ':'OUT'})

    return df

def det_pairs_clusters(df):
    corresponding_synth_clusters = [] ## provar amb un diccionari a veure si els temps milloren?
    if len(df.kmeans_cluster.unique()) == len(df.origin_cluster.unique()):
        for cluster, group in ((df.loc[df['zone'] == "IN"]).groupby("kmeans_cluster")["origin_cluster"]):
            counted_values = group.value_counts().sort_values(ascending=False)
            keys = (counted_values.keys())
            values = counted_values.values
            if keys[0] not in corresponding_synth_clusters:
                print(f"original:{cluster}, synthetic:{keys[0]}, accuracy:{values[0]/values.sum()*100}%.")
                corresponding_synth_clusters.append(keys[0])
            else:
                print("There was a problem, a syth cluster matches with more than one real clusters. aborting...")
                exit(1)
    else:
        print("Number of original clusters and synthetic clusters its different, aborting...")
        exit(1)

    return corresponding_synth_clusters

def calc_rmse(clusters_pairs):
    # read both data files, syth data and real data.
    synth_day = Helper.actual_day
    real_day = synth_day.replace("Synthetic","")

    # real data
    file_route = Helper.project_path+Helper.config_paths['GeneralDirs']['model_creation']+"level"+str(Helper.zone_level)+"/"+Helper.config_paths['SharedDirs']['final_data']+"/"+real_day+".json"
    f = open(file_route,) 
    real_data = json.load(f)
    f.close()

    # syth data
    file_route2 = Helper.project_path+Helper.config_paths['GeneralDirs']['validation']+"level"+str(Helper.zone_level)+"/"+Helper.config_paths['SharedDirs']['final_data']+"/"+synth_day+".json"
    f2 = open(file_route2,) 
    synth_data = json.load(f2)
    f2.close()

    # mean time on clusters
    real_clusters_zonetimes = real_data[real_day]["MeanTimeOnZonesByCluster"]
    synth_clusters_zonetimes = synth_data[synth_day]["MeanTimeOnZonesByCluster"]

    rmse_zonetimes = []
    zones_meantimes = []
    for n, real_zonetime in enumerate(real_clusters_zonetimes):
        synth_zonetime = synth_clusters_zonetimes[clusters_pairs[n]]
        mse = sklearn.metrics.mean_squared_error(real_zonetime, synth_zonetime)
        rmse = math.sqrt(mse)
        rmse_zonetimes.append(rmse)
        zones_meantimes.append( (sum(real_zonetime)) )
        zones_meantimes.append( (sum(synth_zonetime)) )

    real_clusters_matrices = real_data[real_day]["TransitionMatricesByCluster"]
    synth_clusters_matrices = synth_data[synth_day]["TransitionMatricesByCluster"]

    rmse_matrices = []
    for n, real_matrix in enumerate(real_clusters_matrices):
        real_df = pd.DataFrame(real_matrix)

        synth_df = pd.DataFrame(synth_clusters_matrices[clusters_pairs[n]])
        synth_df = synth_df.reindex(sorted(synth_df.columns), axis=1)

        real_df,synth_df = add_non_existing_rows_and_cols(real_df,synth_df)

        real_list = df_values_to_list(real_df)
        synth_list = df_values_to_list(synth_df)

        mse = sklearn.metrics.mean_squared_error(real_list, synth_list)
        rmse = math.sqrt(mse)
        rmse_matrices.append(rmse)

    # save results to final json
    rmse_dict = defaultdict(dict)

    rmse_dict["time_on_zones"]["mean"] = str(sum(rmse_zonetimes)/len(rmse_zonetimes))+"/"+str(sum(zones_meantimes)/len(zones_meantimes))
    rmse_dict["time_on_zones"]["max"] = str(max(rmse_zonetimes))+"/"+str(max(zones_meantimes))

    rmse_dict["transition_matrix"]["mean"] = sum(rmse_matrices)/len(rmse_matrices)
    rmse_dict["transition_matrix"]["max"] = max(rmse_matrices)

    Helper.add_data_to_json_data(rmse_dict, Helper.actual_day, "RMSE")

def df_values_to_list(df):
    aux = df.values.tolist()
    result = [i for a in aux for i in a]
    return result

def add_non_existing_rows_and_cols(df1, df2):
    # df1
    add_to_df = [i for i in df2.columns if i not in df1.columns]
    for col in add_to_df:
        df1[col] = 0
        df1.loc[col] = 0
    df1 = df1.reindex(sorted(df1.columns), axis=1).sort_index()

    # df2
    add_to_df = [i for i in df1.columns if i not in df2.columns]
    for col in add_to_df:
        df2[col] = 0
        df2.loc[col] = 0
    df2 = df2.reindex(sorted(df2.columns), axis=1).sort_index()
    
    return df1, df2

def run_validation(path, name, zone_level):
    # update acutal day
    Helper.actual_day=name

    print(f"----START VALIDATION {name} LEVEL {zone_level}------------------------")

    # prepate the data
    df = prepare_data(path)

    # get times on zones
    users_vector = UsersBuilding.time_on_zone(df)
    
    # get optimal number of clusters
    cluster_method = Helper.config_exec.getint('execution','cluster_method')
    cluster_method_name = "distortion" if cluster_method == 0 else "inertia"
    n_clusters = Helper.get_data_from_json_or_calc("n_clusters_"+cluster_method_name,(users_vector,cluster_method))
    print(f"Number of clusters according to {cluster_method_name} = {n_clusters}")

    # apply kmeans
    df = UsersBuilding.apply_kmeans(df, users_vector, n_clusters)

    # get the original cluster that each syth cluster corresponds to
    clusters_pairs = det_pairs_clusters(df)

    if Helper.save_plots:
        # create movements between zone plots
        # dont want IN and OUT "zones" in the plots
        UsersBuilding.movements_plots_by_cluster(df[~df.zone.isin(["IN", "OUT"])])

    # create the transition matrix to be used on synthetical usr creation
    UsersBuilding.create_transition_matrix(df)
    plt.close('all') # close all open figues

    # check if usr creation time and usrLivetimeByCluster is calculated, calculate if not
    # doing this here will save time on synthetical usr creation part
    Helper.get_data_from_json_or_calc("UsrCreationTime", df)
    
    # UsersBuilding.calc_avg_usr_livetime_by_cluster(df) # ya no fa falta, no se emplea

    # get and save mean time on builfdings by cluster
    Helper.add_data_to_json_data(Helper.zones_names, Helper.actual_day, "ZonesNames")
    UsersBuilding.calc_mean_time_on_zone_by_clusters(df)

    # at this point can calc rmse
    calc_rmse(clusters_pairs)

    print(f"----END VALIDATION {name} LEVEL {zone_level}--------------------------\n")