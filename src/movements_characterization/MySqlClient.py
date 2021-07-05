import pandas as pd
import os
import mysql.connector
import configparser

db_config = configparser.ConfigParser()
db_config.read('configs/db.ini')

paths_config = configparser.ConfigParser()
paths_config.read('configs/paths.ini')

class MySqlClient(object):
    def __init__(self):
        self.DBConfig = {
            'host': db_config['DB']['DBHost'],
            'user': db_config['DB']['DBUser'],
            'password': db_config['DB']['DBPassword'],
            'port': db_config['DB']['DBPort'],
            'database': db_config['DB']['DBName']
        }

    # open the conexion
    def open_cnx(self):
        self.cnx = mysql.connector.connect(**self.DBConfig)
        self.cursor = self.cnx.cursor(dictionary=True) # with that param then we can select rows for it name
    
    # close the conexion
    def close_cnx(self):
        try:
            if self.cnx.is_connected():
                self.cnx.close()
        except:
            pass
    
    # execut a query
    def query(self, query):
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    # save query to a df
    def query_to_df(self, query):
        return pd.read_sql(query, con=self.cnx)
    
    # save query as a csv 
    def query_to_csv(self, query, file_name, index=True):
        data_dir = paths_config['ModelCreation']['dir_raw_data']
        if not os.path.isdir(data_dir):
            os.makedirs(data_dir)
        pd.read_sql(query, con=self.cnx).to_csv(data_dir+file_name, index=index)

if __name__=='__main__':
    db_client = MySqlClient()
    db_client.open_cnx()
    for num, day in enumerate(range(9,15+1, 1)):
        query = f"SELECT hashed_sta_eth_mac AS mac, ap_name, date_time FROM PROXIMITY WHERE date_time between '2020/11/{day} 00:00:00' and '2020/11/{day} 23:59:59'" 
        name = f"Day{num+1}.csv"
        db_client.query_to_csv(query, name, index=False)
    db_client.close_cnx()