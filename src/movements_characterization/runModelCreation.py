import matplotlib.pyplot as plt
import Threshold
import UsersBuilding
import Helper
import os

def run_model_creation_to_specific_day(day_name, zone_level):
    Helper.init()
    dir_raw_data = Helper.project_path+Helper.config_paths['GeneralDirs']['model_creation']+Helper.config_paths['SharedDirs']['raw_data']
    name = day_name
    path = dir_raw_data+name+".csv"
    run_model_creation(path, name, zone_level)

def run_model_creation(path, name, zone_level):
    # update acutal day
    Helper.actual_day=name

    # set zone_level as a global var
    Helper.new_global("zone_level", zone_level)

    print(f"----START MODEL CREATION {name} LEVEL {zone_level}------------------------")

    # prepare the data of that day
    df = Threshold.prepare_data(path)

    # get the optimal threshold
    threshold = Helper.get_data_from_json_or_calc("Threshold",df)
    print(f"Threshold = {threshold}")

    # Adapt df to threshold value and get usrs time on zones
    df, users_vector = UsersBuilding.get_times_on_zone(df, threshold)
    
    # get optimal number of clusters
    cluster_method = Helper.config_exec.getint('execution','cluster_method')
    cluster_method_name = "distortion" if cluster_method == 0 else "inertia"
    n_clusters = Helper.get_data_from_json_or_calc("n_clusters_"+cluster_method_name,(users_vector,cluster_method))
    print(f"Number of clusters according to {cluster_method_name} = {n_clusters}")

    # apply kmeans
    df = UsersBuilding.apply_kmeans(df, users_vector, n_clusters)

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

    print(f"----END MODEL CREATION {name} LEVEL {zone_level}--------------------------\n")
