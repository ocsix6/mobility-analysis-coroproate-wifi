import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import collections
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import Helper
import json
import os

import holoviews as hv
from holoviews import opts, dim
# hv.extension('bokeh')
hv.extension('matplotlib')
hv.output(fig='svg', size=200)
#hv.output(fig='png', size=200)

def set_user_id(df, threshold):
    # create the user_id col, from the diff of time and the optimal threshold
    # and the previous zone if zone_level is higher than 0
    splitted_level = Helper.zone_level.split('.')
    if len(splitted_level) > 1 and int(splitted_level[0]) > 0:
        # lvl > 0
        #df["user_id"] = ((df['diff'] > threshold) | (df['hashed_mac'] != df['hashed_mac'].shift()) | (df['father_zone'] != df['father_zone'].shift())).cumsum()
        #df["user_id"] = ((df['diff']>threshold) | (df['hashed_mac'] != df['hashed_mac'].shift()) | ( (df['father_zone'] != df['father_zone'].shift()) & ( ~df['father_zone'].isin(Helper.active_father_zones) |  ~df['father_zone'].shift().isin(Helper.active_father_zones)) )).cumsum()
        df["user_id"] = ((df['diff']>threshold) | (df['hashed_mac'] != df['hashed_mac'].shift()) | ( (df['father_zone'] != df['father_zone'].shift()) & ( (df['father_zone'] != Helper.active_father_zone) |  (df['father_zone'].shift() != Helper.active_father_zone) ) )).cumsum()
    else:
        # lvl 0
        df["user_id"] = ((df['diff'] > threshold) | (df['hashed_mac'] != df['hashed_mac'].shift())).cumsum()

    # make the user_id as index
    df.index = df.user_id

    return df


def clean_df(df):
    # delete from the df the samples with only 1 conection
    aux = df["user_id"].value_counts()
    df = df[df["user_id"].isin(aux.index[aux.gt(1)])]

    # drop unnecesary cols
    df = df.drop(columns=['hashed_mac', 'diff', 'user_id'])

    splitted_level = Helper.zone_level.split('.')
    if len(splitted_level) > 1 and int(splitted_level[0]) > 0:
        df = df.drop(columns=['father_zone'])

    return df


def set_zone(df):
    # read json and set zones
    # remove all zones that are not of that level

    zones_info = Helper.read_json_file(Helper.project_path+Helper.config_paths['GeneralDirs']['info_zones']+"zonesLevel"+str(Helper.zone_level)+".json")

    # set zones_names as a global var
    Helper.new_global("zones_names", list(zones_info.keys()))

    df["zone"] = df["ap_name"].apply(lambda x: Helper.get_zone_name_from_dict(x, zones_info))

    # remove rows with rm value in zone col (samples that are not of any zone of the actual level)
    df = df[df.zone != "rm"]

    return df


def times_to_percentage(vector, total_time):
    for n, element in enumerate(vector):
        vector[n] = element/total_time*100
    return vector


def clean_repeated(df):
    # the index should be the user_id
    # necessary to create the aux col because the drop_duplicate
    # function dont detect the index col by its name
    df["aux"] = df.index
    df["aux2"] = (df.zone != df.zone.shift()).cumsum()
    df = df.drop_duplicates(subset=['aux', 'aux2'])
    df = df.drop(columns=["aux", "aux2"])
    return df


def add_in_out(df):
    in_df = df.groupby("user_id").first()
    in_df["zone"] = "AAA"

    out_df = df.groupby("user_id").last()
    out_df["zone"] = "ZZZ"

    df = df.append(in_df)
    df = df.append(out_df)

    df = df.sort_values(by=['user_id', 'date_time', 'zone'], ascending=True)
    df['zone'] = df['zone'].replace({'AAA': 'IN'})
    df['zone'] = df['zone'].replace({'ZZZ': 'OUT'})

    return df


def time_on_zone(df):
    # create the vector for all users
    global first_zone_time, last_zone_time, actual_zone_time, actual_zone
    users = []
    # loop through every user
    for user_id, user_data in df.groupby('user_id'):
        # initialize vector of % time in Buildings
        zones = []
        for i in range(0, len(Helper.zones_names)):
            zones.append(0)

        # loop through every user connection
        for i, (u_id, sample) in enumerate(user_data.iterrows()):
            # first connection, imporant to save the time
            if i == 0:
                # this is the IN row
                # we dont want to do nothing in this case
                # because next row will start in exactly same time than that
                pass

            elif i == 1:
                first_zone_time = sample.date_time
                # initialize actual zone values
                actual_zone = sample.zone
                actual_zone_time = sample.date_time

            # if has changed of zone or is the last sample, add the connection time to the respective zone

            else:
                # dont need to check if has changed of zone or is the last zone because we know
                # that the zone of row i is different than row i+1, always

                # add the connection time to the respective zone (in seconds)
                zones[Helper.get_zone_index(actual_zone)] += (sample.date_time - actual_zone_time) / np.timedelta64(1, 's')
                # update actual zone values
                actual_zone = sample.zone
                actual_zone_time = sample.date_time

            # save last connection time
            if i == len(user_data) - 1:
                last_zone_time = sample.date_time

        # calculate total connection time (in seconds)
        total_user_time = (last_zone_time-first_zone_time) / np.timedelta64(1, 's')

        # convert the times to percentatges
        zones = times_to_percentage(zones, total_user_time)

        # add it to the users vector
        users.append(zones)

    if Helper.save_jsons:
        dir_json = Helper.get_route_according_validation('time_on_building')

        Helper.create_dir_if_not_exists(dir_json)

        with open(dir_json+"time_on_zone"+Helper.actual_day+".json", 'w') as fp:
            json.dump(users, fp,  indent=3)

    return users


def get_times_on_zone(df, threshold):
    df = set_user_id(df, threshold)
    df = set_zone(df)
    df = clean_df(df)
    df = add_in_out(df)
    df = clean_repeated(df)
    users_vector = time_on_zone(df)

    if Helper.save_csvs:
        # save csv before apply clustering
        dir_df = Helper.get_route_according_validation('df_before_clustering')
        Helper.create_dir_if_not_exists(dir_df)
        df.to_csv(dir_df+Helper.actual_day+".csv")

    return df, users_vector


def apply_kmeans(df, vectors, n_clusters):
    # https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html

    n_clusters = int(n_clusters)

    # define the model
    model = KMeans(random_state=6969, n_clusters=n_clusters)

    # fit the model
    model.fit(vectors)

    # assign a cluster to each sample
    users_groups = model.predict(vectors)

    # add cluster results to df
    # create an auxiliar df with the clusters of each user
    aux_data = {"user_id": df.index.unique(),"kmeans_cluster": users_groups}
    aux_df = pd.DataFrame(aux_data)
    # join the aux_df
    df = df.merge(aux_df, on="user_id", how="left")
    df.index = df.user_id
    df = df.drop(columns=["user_id"])

    # lets plot the number of users of each cluster

    # Dict with number of each type of user
    n_type_users = collections.Counter(users_groups)
    # order the dict by key
    n_type_users = collections.OrderedDict(sorted(n_type_users.items()))

    # save % of users of each cluster
    usr_in_cluster = list(n_type_users.values())
    usr_in_cluster = times_to_percentage(usr_in_cluster, sum(usr_in_cluster))

    # save it to the json that contains different data
    Helper.add_data_to_json_data(
        usr_in_cluster, Helper.actual_day, "PercentUsrCluster")
    print("Calculated and saved percentage of users for each cluster.")

    if Helper.save_plots:
        # plot
        plt.bar(range(len(n_type_users)), list(n_type_users.values()), align='center')
        plt.xticks(range(len(n_type_users)), list(n_type_users.keys()))
        plt.title('Number of users of each type according KMeans', fontsize=18)
        plt.xlabel(r"Type of user", fontsize=18)
        plt.ylabel(r"Number of users", fontsize=18)
        dir_users_cluster = Helper.get_route_according_validation('n_users_by_cluster')
        Helper.create_dir_if_not_exists(dir_users_cluster)
        plt.savefig(dir_users_cluster+(f"usersByCluster{Helper.actual_day}.pdf"))
        plt.close()

    if Helper.save_jsons:
        dir_json = Helper.get_route_according_validation('users_groups')

        if(not os.path.isdir(dir_json)):
            os.makedirs(dir_json)

        with open(dir_json+"users_groups"+Helper.actual_day+".json", 'w') as fp:
            json.dump(users_groups.tolist(), fp,  indent=3)

    if Helper.save_csvs:
        # save that final df to a csv
        directory = Helper.get_route_according_validation('df_after_kmeans')
        Helper.create_dir_if_not_exists(directory)
        df.to_csv(directory+Helper.actual_day+".csv")

    return df


def prepare_data_zone_mov(group):
    zone_names, edges = [], []
    # route o zones of all users of same cluster
    for zone in group.values:
        # route of zones of one particular user
        aux = 0
        n = len(zone)
        if n > 1:
            zone_names = zone_names+zone
        while n > aux+1:
            edges.append((zone[aux], zone[aux+1]))
            aux += 1

    # this list of zones does not contain all zones, only the zones
    # that this cluster interacts with
    zone_names = list(set(zone_names))  # remove duplicate zones
    
    # Frequency of movements among zones
    mov_freq = dict(collections.Counter(edges))

    return zone_names, mov_freq


def plot_chord(zone_names, mov_freq, name):
    # Prepare data for chord plot
    source, target, value = [], [], []

    for item in mov_freq.items():
        source.append(item[0][0])
        target.append(item[0][1])
        value.append(item[1])

    edge_zone = pd.DataFrame(
        {"source": source, "target": target, "value": value})  # links
    node_zone = hv.Dataset(pd.DataFrame({"zone": zone_names}))

    # Matplotlib way
    chord = hv.Chord((edge_zone, node_zone)).opts(
        opts.Chord(cmap='Category20', edge_color=dim('source').astype(str), labels='zone', node_color=dim('zone').astype(str),title=f'Movements cluster {name}', sublabel_format=""))

    return chord


def prepare_prob_matrix_data(zone_names, mov_freq):
    total_movements = sum(mov_freq.values())
    zone_names = sorted(zone_names)
    # each zone with it position in the array of names
    map_id_zone = dict(zip(zone_names, range(len(zone_names))))

    # initialize the probability matrix with zeros
    freq = np.zeros((len(zone_names), len(zone_names)))
    # fill the matrix with the values
    for x, y in mov_freq:
        freq[map_id_zone[x], map_id_zone[y]] = (mov_freq[(x, y)]/total_movements)*100
    return zone_names, freq


def plot_prob_matrix(zone_names, mov_freq, name):
    zone_names, freq = prepare_prob_matrix_data(zone_names, mov_freq)
    # create the plot
    fig, ax = plt.subplots()

    c = ax.pcolor(freq, edgecolors='k', linewidths=4)
    ax.set_title(f'Movements between zones cluster {name}')

    ax.set_xticks(np.arange(len(zone_names)) + 0.5, minor=False)
    ax.set_yticks(np.arange(len(zone_names)) + 0.5, minor=False)

    ax.set_xticklabels(zone_names, rotation=90)
    ax.set_yticklabels(zone_names)

    fig.tight_layout()
    return plt


def movements_plots_by_cluster(df):
    global combined_plot, combined_plot
    dir_chords = Helper.get_route_according_validation('chord_plots')
    dir_prob_matrix = Helper.get_route_according_validation('p_matrix_plots')
    Helper.create_dir_if_not_exists(dir_chords)
    Helper.create_dir_if_not_exists(dir_prob_matrix)
    # create the pdf
    matrix_plots = PdfPages(dir_prob_matrix+(f"matrix_plots{Helper.actual_day}.pdf"))

    # list of all chord plots
    chords = []

    for cluster, group in df.groupby("kmeans_cluster")["zone"]:
        l_zones = group.groupby("user_id").apply(list)
        zone_names, mov_freq = prepare_data_zone_mov(l_zones)
        if mov_freq: 
            # because it can be the case that all those in the cluster are always in the same zone
            # and the chords only show movements between zones
            chords.append(plot_chord(zone_names, mov_freq, cluster))
            plot_prob_matrix(zone_names, mov_freq, cluster).savefig(
                matrix_plots, format='pdf', bbox_inches='tight')
            plt.close()

    # close the pdf of the plots
    matrix_plots.close()

    # save chords to html
    for n, chord in enumerate(chords):
        if n == 0:
            combined_plot = chord
        else:
            combined_plot = combined_plot + chord

    hv.save(combined_plot, dir_chords +
            (f'chords{Helper.actual_day}.html'))


def create_transition_matrix(df):
    matrices_vector = []
    for cluster, group in df.groupby("kmeans_cluster")["zone"]:
        l_zones = group.groupby("user_id").apply(list)
        zone_names, mov_freq = prepare_data_zone_mov(l_zones)  # !!!!!!!
        zone_names, freq = prepare_prob_matrix_data(zone_names, mov_freq)
        # df with the probabilities of movements between zones
        prob_df = pd.DataFrame(freq, columns=zone_names, index=zone_names)

        # append all csv in a vector, in json form
        matrices_vector.append(json.loads(prob_df.to_json()))

    # save the vector with all transition matrices
    Helper.add_data_to_json_data(
        matrices_vector, Helper.actual_day, "TransitionMatricesByCluster")


def calc_usr_creation_time(df):
    # in minutes
    return (df.groupby("user_id")["date_time"].first().sort_values().diff().mean()) / np.timedelta64(1, 'm')


def calc_avg_usr_livetime_by_cluster(df):
    times = []
    users_by_clusters = df.groupby("kmeans_cluster")
    for name, group in users_by_clusters:
        users_date_time = group.groupby(["user_id"])["date_time"]
        con_times = users_date_time.last() - users_date_time.first()
        # mean of the connection times in seconds
        mean_con_times = con_times.mean().total_seconds()/60
        times.append(mean_con_times)

    # save it to the json that contains different data
    Helper.add_data_to_json_data(times, Helper.actual_day,
                             "AvgUsrLiveTimeByCluster")
    print("Calculated and saved average user live time by cluster.")


def calc_mean_time_on_zone_by_clusters(df):
    list_zone_times_clusters = []
    
    for name, group in df.groupby("kmeans_cluster"):
        # initialize vector of times and vector of number of entries
        zone_times = []
        zone_entries = []
        for i in range(0, len(Helper.zones_names)):
            zone_times.append(0)
            zone_entries.append(0)

        # initialize actual zone to invalid value
        actual_zone = ""
        actual_zone_time = ""

        # loop through every user connection
        for u_id, sample in group.iterrows():
            if actual_zone != "IN" and actual_zone != "OUT" and actual_zone != "":
                # get the time in minutes
                zone_times[Helper.get_zone_index(
                    actual_zone)] += (sample.date_time - actual_zone_time) / np.timedelta64(1, 'm')
                zone_entries[Helper.get_zone_index(actual_zone)] += 1

            # update actual zone
            actual_zone = sample.zone
            actual_zone_time = sample.date_time

        # get mean times
        for n, element in enumerate(zone_times):
            if zone_entries[n] == 0:
                pass
            else:
                zone_times[n] = element / zone_entries[n]

        list_zone_times_clusters.append(zone_times)

    # save it to the json that contains different data
    Helper.add_data_to_json_data(list_zone_times_clusters,
                             Helper.actual_day, "MeanTimeOnZonesByCluster")
    print("Calculated and saved mean time on zones by cluster.")