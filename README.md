# User mobility analysis in a coorporate WiFi network using data mining techniques.

## Explanation

This project presents a study on the generation of synthetic data from models of user mobility in WiFi connections. The mobility data has been collected through the Wi-Fi infrastructures of the campus of the University of the Balearic Islands (UIB). This infrastructure includes Analytics and Location Engine (ALE) technology, a Wi-Fi Analytics tool that allows collecting presence and location data from devices through your Wi-Fi network.

The study and modeling of mobility will generate synthetic mobility models that can be shared publicly and can be used in other studies, such as for the planning of evacuation strategies or planning of ICT services capacity. To carry out this project, three phases have been proposed: data collection, definition of the model and generation of synthetic data.

The entire methodology is complemented by a study case within the UIB campus. The results obtained, broad and representative, allow to visualize the behavior of the different groups of users and their movements between areas of the campus. Furthermore, the synthetically generated data set is very similar to the real set, as expected from the beginning.

This repository contains a set of scripts that automate the different phases of this mobility analysis.

## Requirements
- Python 3.7.9
- Python libraries specified at requirements.txt file.

## How to install
1. Clone the repo.
2. Install the required libraries. It is recommended to create a new virtual environment with the specified python version.

## How to use
Once the source code has been downloaded and the environment prepared the program is ready to use. But first it is necessary to know some important aspects:
- There are two clearly differentiated parts: the collection and storage of the data and the characterization of the movements. These are completely independent of each other.
- Data collection aspects:
  - It has two configuration files, one specific for the ALE and the other for the directories names and the access to the DB to save the collected info.
  - The different collection scripts run independently and are intended to be added to the cron to run periodically. Except for *access_point*, which is recommended to run once at startup, it will be called later by the other scripts if necessary.
- Movements characterization aspects:
  - It presents several configuration files under the /configs path. The only one that is essential to modify is bdSample.ini which must be renamed to bd.ini after completing the fields it contains.  
  The exec.ini file presents different execution configurations that will be applied when executing the *run* script. All the configurable parameters are explained in the file itself.  
  The paths.ini file contains the selected paths for storing the data, both input and output.
  - The input data must be stored in the path specified in the configuration file (paths.ini), in csv format. It is recommended to divide the data set into smaller subsets as long as the similarity of movements in the different subsets is not known. The structure of the data must be as follows (the column names are important):
  ```
    hashed_mac,ap_name,date_time
    mac1,ap1,2000-01-01 00:00:00
    mac2,ap2,2000-01-01 00:01:00
    ...
  ```
  - Level definition JSON files must be provided and stored in the path indicated according to the configuration file (paths.ini). Each level is made up of different zones, where each of these is made up of different access points. An access point can belong to only one zone.  
  At least one level must be defined (zonesLevel0.json). Then, the rest of the levels that are defined must meet the condition that all the APs of the level have to belong to a single zone of the previous level. This is a required and necessary condition, which is checked in execution. Different levels allow studies with different depth.
  Example of a level definition file:  
  ```
  {
      "zone1": [
          AP1,
          AP2
      ],
      "zone2": [
          AP3,
          AP4
      ],
      ...
  }
  ```

  - The different scripts are called automatically according to the configuration indicated in the exec.ini file when executing the *run* file, therefore this is the only file that must be executed by the user.

## Results
The main output of the user characterization scripts are the different models obtained. The models are formed by a transition matrix between zones and time vectors in zones. Apart from these, other outputs are generated such as, chords representing the movement between zones, boxplots with the number of users per cluster, heatmaps, graphical representations of the calculation of the optimal number of clusters, etc. All these results of the study case carried out are provided.


## Clarifications
This repository only contains the source code of the project and the results of the UIB study case. Neither original nor synthetically generated data is available. Although the latter can be generated from the models, which are available.

## License
MIT.