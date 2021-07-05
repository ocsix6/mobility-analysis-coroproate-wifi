import Helper
import os
import SynthethicGeneration
import runModelCreation

def run_synth_usr_creation_to_specific_day(day_name, zone_level):
    #dir_raw_data = Helper.config_paths['SynthGeneration']['dir_raw_data']+"level"+str(zone_level)+"/"
    Helper.init()
    dir_raw_data = Helper.project_path+Helper.config_paths['GeneralDirs']['model_creation']+"level"+str(zone_level)+"/"+Helper.config_paths['SharedDirs']['final_data']
    path = dir_raw_data+day_name+".json"
    #path = dir_raw_data+day_name+"/" # all csv in a dir way
    Helper.new_global("zone_level", zone_level)
    if os.path.isfile(path):
        runSynthUsrCreation(path, day_name, zone_level)
    else:
        print(f"Dont have info about clusters of {day_name}, needed to run Model Creation for that specific day...")
        runModelCreation.run_model_creation_to_specific_day(day_name, zone_level)
        runSynthUsrCreation(path, day_name, zone_level)


def runSynthUsrCreation(path, name, zone_level):
    # update acutal day
    Helper.actual_day=name

    print(f"----START SYNTHETIC USER GENERATION {name} LEVEL {zone_level}------------------------")

    clusters_dfs = SynthethicGeneration.read_all_transition_matrices(path)

    # read start time and duration from exec config file
    start_time = Helper.config_exec.get('synthetic_generation','start_time').split(":")
    start_time = [ int(x) for x in start_time ]
    
    if 0 < start_time[0] < 24:
        start_hour = start_time[0]
    else:
        start_hour = 8
        print(f"start_hour auto defined with a value of {start_hour} because the one introduced is not between 0 and 24")

    if 0 < start_time[1] < 60:
        start_min = start_time[1]
    else:
        start_min = 0
        print(f"start_min auto defined with a value of {start_min} because the one introduced is not between 0 and 60")

    duration_minutes = Helper.config_exec.getint('synthetic_generation','minutes_duration')
    if duration_minutes < 0:
        duration_minutes = 120
        print(f"duration_minutes auto defined with a value of {duration_minutes} because the one introduced is lower than 0")

    usr_creation_time, percent_usr_cluster, mean_time_on_buildings_by_cluster = SynthethicGeneration.prepare_needed_data()

    SynthethicGeneration.create_day_path(start_hour, start_min, duration_minutes, clusters_dfs, usr_creation_time, percent_usr_cluster, mean_time_on_buildings_by_cluster)

    print(f"----END SYNTHETIC USER GENERATION {name} LEVEL {zone_level}--------------------------\n")
