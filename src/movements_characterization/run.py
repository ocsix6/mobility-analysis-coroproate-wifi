import runModelCreation
import runSynthUsrCreation
import Helper
import os
import re
import runValidation

def main():
    Helper.init()
    
    if Helper.config_exec.getboolean('execution','execute_all_levels'):
        execution_levels = [file for file in os.listdir(Helper.project_path+Helper.config_paths.get('GeneralDirs','info_zones')) if file.endswith(".json")]
        execution_levels = [level.split('.',2)[0] for level in execution_levels]
        # regex to get only the numbers of the level
        execution_levels = [re.findall(r'([A-Za-z]*)([0-9.]+)', name)[0][-1] for name in execution_levels]
        execution_levels = [int(aux) for aux in execution_levels]
        execution_levels.sort()
    else:
        execution_levels = Helper.config_exec.get('execution','execution_levels').split(',')
        #execution_levels = [name + ".json" for name in execution_levels]
        execution_levels = [name for name in execution_levels]
    
    if Helper.config_exec.getboolean('execution','execute_all_csv_files'):
        #execution_csv = [file for file in os.listdir(Helper.project_path+Helper.config_paths.get('GeneralDirs','model_creation')+Helper.config_paths.get('SharedDirs','raw_data')) if file.endswith(".csv")]
        execution_csv = [os.path.splitext(file)[0] for file in os.listdir(Helper.project_path+Helper.config_paths.get('GeneralDirs','model_creation')+Helper.config_paths.get('SharedDirs','raw_data')) if file.endswith(".csv")]
    else:
        execution_csv = Helper.config_exec.get('execution','csv_data_file_names').split(',')
        #execution_csv = [file + ".csv" for file in execution_csv]
    
    # option for synthetic csv files

    execute_selected_options(execution_levels, execution_csv)

def execute_selected_options(execution_levels, execution_csv):
    if Helper.config_exec.getboolean('execution','execute_all_parts'):
        execute([0,1,2], execution_levels, execution_csv)
    else:
        options = Helper.config_exec.get('execution','execution_parts').split(',')
        options = [int(option) for option in options]
        execute(options, execution_levels, execution_csv)

# args:
# option:
#   0 : model creation
#   1 : sinthetic usr creation
#   2: validation
def execute(options, execution_levels, csv_files):
    for level in execution_levels:
        for file in csv_files:
            for option in options:
                if option == 0:
                    runModelCreation.run_model_creation_to_specific_day(file, level)
                elif option == 1:
                    runSynthUsrCreation.run_synth_usr_creation_to_specific_day(file, level)
                elif option == 2:
                    #Validation.run_validation_to_specific_day(file+"Synthetic", level)
                    runValidation.run_validation_to_specific_day(file, level)
                else:
                    print("No valid method")

if __name__ == '__main__':
    main()