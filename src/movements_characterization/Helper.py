import os
import Threshold
import UsersBuilding
import Cluster
import configparser
import json
from collections import defaultdict


def get_project_path(file_name="README.md", actual_path=None):
    """

    :param file_name: name of a file in the top level of the project
    :param actual_path: actual path, if not specified its calculated
    :return: global path of the project
    """
    if not actual_path:
        actual_path = os.path.dirname(os.path.abspath(file_name))
    if os.path.isfile(actual_path+"/"+file_name):
        return actual_path
    else:
        return get_project_path(file_name, os.path.abspath(os.path.join(actual_path, os.pardir)))

def init(paths_config="paths", exec_config="exec"):
    """

    :param paths_config: name of paths config file
    :param exec_config: name of exec config file
    :return: none
    """
    global actual_day, project_path, config_paths, config_exec, save_plots, save_jsons, save_csvs
    # string to know the actual day through all files
    actual_day = ""
    project_path = get_project_path()+"/"
    # Read the config file
    config_paths = configparser.ConfigParser()
    config_paths.read(project_path+'src/movements_characterization/configs/'+paths_config+'.ini')
    config_exec = configparser.ConfigParser()
    config_exec.read(project_path+'src/movements_characterization/configs/'+exec_config+'.ini')
    save_jsons = config_exec.getboolean('aux_files','json_files')
    save_plots = config_exec.getboolean('aux_files','plots')
    save_csvs = config_exec.getboolean('aux_files','csvs')

def new_global(name, value):
    globals()[name] = value

def get_zone_index(name):
    return zones_names.index(name)

def get_data_from_json_or_calc(wanted_data, call_param = None):
    dir_route = get_route_according_validation('final_data')
    day = actual_day
    file_route = dir_route+day+".json"

    def calcValue():
            if wanted_data=="Threshold": return Threshold.get_optimal_threshold(call_param)
            elif wanted_data=="n_clusters_distortion" or wanted_data=="n_clusters_inertia": return Cluster.get_optimal_clusters(call_param)
            elif wanted_data=="UsrCreationTime": return UsersBuilding.calc_usr_creation_time(call_param)

    if os.path.isfile(file_route):
        # Opening JSON file 
        f = open(file_route,) 

        # returns JSON object as a dictionary 
        dict_data = json.load(f) 

        try:
            value =  dict_data[day][wanted_data]
            print(f"{wanted_data} found in memory, using it.")
            f.close()
            return value
        except KeyError:
            print(f"{wanted_data} not in memory, calculating...")
            dict_data = defaultdict(dict, dict_data)
            value = calcValue()
            dict_data[day][wanted_data] = value
            save_to_json(dict_data, file_route)
            f.close()
            return value

    else:
        print("File with different processed data dont found, creating...")
        dict_data = defaultdict(dict)
        print(f"{wanted_data} not in memory, calculating...")
        value = calcValue()
        dict_data[day][wanted_data] = value
        create_dir_if_not_exists(dir_route)
        save_to_json(dict_data, file_route)
        return value

def add_data_to_json_data(data, day, param):
    file_route = get_route_according_validation('final_data')+actual_day+".json"
    # Opening JSON file 
    f = open(file_route,) 
    # returns JSON object as a dictionary 
    dict_data = json.load(f) 
    dict_data = defaultdict(dict, dict_data)
    dict_data[day][param] = data
    save_to_json(dict_data, file_route)
    f.close()

def save_to_json(data, route):
    with open(route, "w") as fp:
        json.dump(data, fp, indent=3)

def read_json_file(path):
    with open(path) as json_file: 
        aux = json.load(json_file)
    return aux

def create_dir_if_not_exists(dir):
    if not os.path.isdir(dir):
        f_dir = dir.split("/")
        size = len(f_dir)
        for sub_dir in f_dir:
            if sub_dir == ".." or sub_dir == "":
                size -= 1
        if size > 1:
            os.makedirs(dir)
        else:
            os.mkdir(dir)

def get_route_according_validation(element):
    if 'validation' in globals():
        if validation:
            return project_path+config_paths['GeneralDirs']['validation']+"level"+str(zone_level)+"/"+config_paths['SharedDirs'][element]
    # other cases
    return project_path+config_paths['GeneralDirs']['model_creation']+"level"+str(zone_level)+"/"+config_paths['SharedDirs'][element]

def get_zone_name_from_dict(ap_name, zones_dict):
    for zone, zone_vector in zones_dict.items():
        if ap_name in zone_vector:
            return zone
    return "rm"

def check_if_study_zone(ap_name, zones_dict):
    if ap_name in zones_dict[active_father_zone]:
        return "yes"
    return "rm"