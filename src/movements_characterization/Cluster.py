from sklearn.cluster import KMeans
from scipy.spatial.distance import cdist
from kneed import KneeLocator
import matplotlib.pyplot as plt
import numpy as np
import Helper
import warnings

##
# params:
#   users_vectors: time users vector
#   method: 0: distortion, 1: intertia
##
def get_optimal_clusters(params):
    users_vectors = params[0]
    method = params[1]
    with warnings.catch_warnings():
	# ignore all caught warnings
        warnings.filterwarnings("ignore")
        values = calculate_values(users_vectors, method)
    if Helper.save_plots:
        plot_clusters(values,method)
    n_clusters = optimal_n_clusters(values)
    return int(n_clusters)

def optimal_n_clusters(values):
    # https://stackoverflow.com/questions/51762514/find-the-elbow-point-on-an-optimization-curve-with-python
    kn = KneeLocator(list(values.keys()), list(values.values()), curve='convex', direction='decreasing')
    return kn.knee

def plot_clusters(values, method_num):
    method = "Distortion" if method_num == 0 else "Inertia"
    plt.plot(values.keys(), values.values(), 'bx-') 
    plt.xlabel('Number of clusters') 
    plt.ylabel(f'{method}') 
    plt.title(f'Elbow Method of {Helper.actual_day} using {method}') 
    plot_dir = Helper.get_route_according_validation('kmean_n_clusters_plots')
    Helper.create_dir_if_not_exists(plot_dir)
    plt.savefig(plot_dir+Helper.actual_day+method+".png")
    plt.close()

def calculate_values(user_vectors, method=0):
    user_vectors=np.array(user_vectors)
    values = {}
    top_value = 30 + 1
    top_value = top_value if len(user_vectors) > top_value else len(user_vectors)
    K = range(1,top_value) # necessary low left value for the cases where the levels contains few zones
    
    for k in K:
        kmean_model = KMeans(n_clusters=k, random_state=6969)
        kmean_model.fit(user_vectors)
        if method==0:
            values[k] = sum(np.min(cdist(user_vectors, kmean_model.cluster_centers_, 
                'euclidean'),axis=1)) / user_vectors.shape[0]
        elif method==1:
            values[k]=kmean_model.inertia_
    return values