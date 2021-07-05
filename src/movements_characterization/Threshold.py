import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_pdf import PdfPages
import Helper

def get_optimal_threshold(df):
    threshold_table = get_thresholds_table(df)
    threshold_table = calculate_euclidean_dist(threshold_table)
    best_threshold = get_min_distance(threshold_table)

    return int(best_threshold)

def get_studying_father_zone(father_level_info, actual_level_info):
    actual_level_aps = []
    
    # get all the aps of actual zone
    for key in actual_level_info:
        actual_level_aps.extend([ap for ap in actual_level_info[key]])

    # add father zone if the ap is an ap of the actual zone level
    prev_father_level = None
    father_level = None
    
    for key in father_level_info:
        updated = False

        for ap in father_level_info[key]:
            if ap in actual_level_aps:
                father_level = key
                updated = True
                break
                
        if updated:
            if prev_father_level:
                if prev_father_level != father_level:
                    print("This zoneLevel contains APs from more than one zone of its father level.\nThat's not permited, redefine the zone level and run the script again.")
                    exit(1)
        
            prev_father_level = father_level

    return father_level


def level_processing(df):
    splitted_level = Helper.zone_level.split('.')
    if len(splitted_level) > 1 and int(splitted_level[0]) > 0:
        aux = splitted_level[:-1]
        aux[0] = str(int(aux[0]) - 1)
        father_level = '.'.join(aux)
        ##
        father_level_info = Helper.read_json_file(Helper.project_path+Helper.config_paths['GeneralDirs']['info_zones']+"zonesLevel"+father_level+".json")
        actual_level_info = Helper.read_json_file(Helper.project_path+Helper.config_paths['GeneralDirs']['info_zones']+"zonesLevel"+Helper.zone_level+".json")
        # define the active_father_zones as a global value of Helper
        Helper.new_global("active_father_zone", get_studying_father_zone(father_level_info,actual_level_info))

        #df["father_zone"] = df["ap_name"].apply(lambda x: Helper.get_zone_name_from_dict(x,father_level_info))
        df["father_zone"] = df["ap_name"].apply(lambda x: Helper.check_if_study_zone(x,father_level_info))

    return df

def prepare_data(route):
    # Load the dataset
    df = pd.read_csv(route)

    # convert to datetime
    df['date_time'] = pd.to_datetime(df['date_time'])
    
    # order by mac and date_time
    df = df.sort_values(by=['hashed_mac', 'date_time'],ascending=True)

    # new column that indicates the time difference between that sample and the previous one of the same mac (in minutes)
    df['diff'] = df['date_time'].sub(df.groupby('hashed_mac')['date_time'].shift()).dt.total_seconds()/60

    df = level_processing(df)

    return df

def get_thresholds_table(df):
    # Loop through all threshold values (in minutes)
    min_threshold = 5 # if start from 1, 2 or 3, it has problems (it detects the min there)
    max_threshold = 500
    splitted_level = Helper.zone_level.split('.')
    
    # Dic to save the info of all thresholds
    threshold_values = {}

    for threshold in range (min_threshold,max_threshold+1, 1):
        
        # necessary to create a copy, if not, the deleted rows of one threshold will affect the next thresholds.
        df_aux = df.copy()

        # the id will also depend if the zone_level is 0 (dont have father zone) or not (it has father zone)
        if len(splitted_level) > 1 and int(splitted_level[0]) > 0:
            # lvl > 0
            df_aux["id"] = ((df_aux['diff']>threshold) | (df_aux['hashed_mac'] != df_aux['hashed_mac'].shift()) |  (df_aux['father_zone'] != df_aux['father_zone'].shift()) ).cumsum()
        else:
            # lvl = 0
            df_aux["id"] = ((df_aux['diff']>threshold) | (df_aux['hashed_mac'] != df_aux['hashed_mac'].shift())).cumsum()

        # delete from the df the samples with only 1 conection
        aux = df_aux["id"].value_counts()
        df_aux = df_aux[df_aux["id"].isin(aux.index[aux.gt(1)])]
        
        # get number of total users
        total_users=df_aux["id"].nunique() # Count number of unique id, each id is a user
        
        # get the connection time for each user and the mean
        users_date_time = df_aux.groupby("id")["date_time"]
        con_times = users_date_time.last() - users_date_time.first()
        mean_con_times = con_times.mean().total_seconds() # mean of the connection times in seconds
        
        threshold_values[threshold] = [threshold, total_users, mean_con_times] # save to the dic

    # Create a table with the info of the different thresholds
    threshold_table = pd.DataFrame.from_dict(threshold_values, orient='index',
                        columns=['Threshold', 'N_users', 'Mean_Time'])

    return threshold_table

def calculate_euclidean_dist(threshold_table):
    # lets get the min and max values to normalize
    min_n_users = threshold_table.N_users.min()
    max_n_users = threshold_table.N_users.max()

    min_mean_time = threshold_table.Mean_Time.min()
    max_mean_time = threshold_table.Mean_Time.max()

    # Normalize
    threshold_table["N_users"] = threshold_table["N_users"].apply(lambda x : (x-min_n_users)/(max_n_users-min_n_users))
    threshold_table["Mean_Time"] = threshold_table["Mean_Time"].apply(lambda x : (x-min_mean_time)/(max_mean_time-min_mean_time))

    # Calculate euclidean distance
    threshold_table["EuclideanDist"] = np.sqrt(threshold_table["N_users"].pow(2)+threshold_table["Mean_Time"].pow(2))

    if Helper.save_plots:
        plots_to_pdf(threshold_table)

    return threshold_table

def get_min_distance(threshold_table):
    # get the threshold it belongs to them min distance
    return threshold_table['EuclideanDist'].idxmin() 


def plots_to_pdf(threshold_table):
    # save plot of euclidean distance for all thresholds

    # get the minimum euclidean distance 
    # and its index (the threshold it belongs to)
    min_dist_value = threshold_table['EuclideanDist'].min() 
    min_dist_idx = threshold_table['EuclideanDist'].idxmin() 

    # create the dir if dont exists

    dir_plots = Helper.get_route_according_validation('threshold_plots')

    Helper.create_dir_if_not_exists(dir_plots)
    # create the pdf
    pdf_plots = PdfPages(dir_plots+"Threshold"+Helper.actual_day+".pdf")

    # Lets plot it
    fig, ax = plt.subplots()
    dfp = threshold_table["EuclideanDist"]
    dfp.plot(stacked=True,ax=ax)
    plt.title('Euclidean distances for all thresholds', fontsize=18)
    plt.xlabel(r"Threshold", fontsize=18)
    plt.ylabel(r"Euclidean distance", fontsize=18)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    # good size for axis numbers
    ax.tick_params(axis='both', which='major', labelsize=12) 
    ax.tick_params(axis='both', which='minor', labelsize=8)
    # grid
    ax.grid()
    # save it to the pdf
    plt.savefig(pdf_plots, format='pdf', bbox_inches = 'tight')
    plt.close()

    # zoom in plot
    fig, ax = plt.subplots()
    dfp = threshold_table["EuclideanDist"]
    dfp.plot(stacked=True,ax=ax)
    plt.title('Euclidean distances focused on min', fontsize=18)
    plt.xlabel(r"Threshold", fontsize=18)
    plt.ylabel(r"Euclidean distance", fontsize=18)
    ax.xaxis.set_minor_locator(MaxNLocator(integer=True))
    # good size for axis numbers
    ax.tick_params(axis='both', which='major', labelsize=12) 
    ax.tick_params(axis='both', which='minor', labelsize=8)
    # grid
    ax.grid()
    # X axis limits
    plt.xlim(min_dist_idx-10, min_dist_idx+10)
    plt.xticks(np.arange(min_dist_idx-10, min_dist_idx+10, 1.0))
    # anotate the minimum
    ax.annotate(f'min distance \nx={min_dist_idx}, y={round(min_dist_value,4)}', size =15, xy=(min_dist_idx, min_dist_value), xytext=(min_dist_idx, min_dist_value+0.125),
                arrowprops=dict(facecolor='red', shrink=2))

    plt.savefig(pdf_plots, format='pdf', bbox_inches = 'tight')
    plt.close()

    # close the pdf of the plots
    pdf_plots.close()