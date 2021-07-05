import urllib3
import mysql.connector
import json
from datetime import datetime
from time import time
import os
from config import *
from ale_config import *
from telegramBot import *
##
import logging.config
logging.config.fileConfig(os.getcwd() + '/logging.ini')
logger = logging.getLogger(__name__)
##

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#iniciamos el contador
start_time = time()

print("################## INCIO PROXIMITY.PY ##################")

#Inicio Query ALE
http = urllib3.PoolManager()
url = ALEUrlProximity
# pasamos el usuario y contrasena por headers
headers = urllib3.util.make_headers(basic_auth=ALEUser+':'+ALEPassword)
r = http.request('GET', url, headers=headers)

if r.status == 200:
    print("Query ALE realizada correctamente")
else:
    print("Problemas en Query ALE ")

# pasamos los datos a utf-8
datos = str(r.data, 'utf-8')

if not os.path.isdir(dirJson):
    os.mkdir(dirJson)

if not os.path.isdir(dirJson + "/" + dirProximity):
    os.mkdir(dirJson+"/"+dirProximity)

#Guardamos fecha y hora actual para anadiselo al nombre del fichero
fechaActual=str(datetime.now().replace(microsecond=0))
nombreFichero="proximity_"+fechaActual+".json"
f = open(dirJson+"/"+dirProximity+"/"+nombreFichero, "w")
f.write(datos)
f.close()

datosJson = json.loads(datos)

# connexion a la base de datos

connection = mysql.connector.connect(
    host=BDHost,
    user=BDUser,
    passwd=BDPassword,
    port=BDPort,
    database=BDDatabase
)

cursor = connection.cursor()


insertsUsers = 0
insertsProximity = 0
llamada_access_point = False
# Actualizamos la tabla USER
for x in datosJson["Proximity_result"]:

    deviceType = default_device_type

    # Si este id no esta guardado anteriormente lo guardamos
    mysqlSelect = "SELECT hashed_sta_eth_mac from USER WHERE hashed_sta_eth_mac=%s  LIMIT 1"
    mysqlParams = (x["msg"]["hashed_sta_eth_mac"],)
    cursor.execute(mysqlSelect, mysqlParams)
    records = cursor.fetchall()
    if not records:
        # insert
        sqlInsert = """INSERT INTO USER
                            (hashed_sta_eth_mac, device_type) VALUES (%s, %s)"""
        insertvalues = (x["msg"]["hashed_sta_eth_mac"], deviceType,)
        cursor.execute(sqlInsert, insertvalues)
        connection.commit()
        insertsUsers += 1


    fecha=datetime.fromtimestamp(x["ts"])


    mysqlSelect = "SELECT date_time, hashed_sta_eth_mac, ap_name from PROXIMITY WHERE date_time=%s AND hashed_sta_eth_mac=%s AND ap_name=%s LIMIT 1"
    mysqlParams = (fecha,x["msg"]["hashed_sta_eth_mac"], x["msg"]["ap_name"],)
    cursor.execute(mysqlSelect, mysqlParams)
    records = cursor.fetchall()
    if not records:
        sqlInsert = """INSERT INTO PROXIMITY
                                    (date_time, hashed_sta_eth_mac, ap_name, radio_mac_addr, rssi_val, target_type, json_name) VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        insertvalues = (fecha,x["msg"]["hashed_sta_eth_mac"], x["msg"]["ap_name"], x["msg"]["radio_mac"]["addr"],x["msg"]["rssi_val"], x["msg"]["target_type"], nombreFichero)
        try:
            cursor.execute(sqlInsert, insertvalues)
            connection.commit()
            insertsProximity += 1

        except mysql.connector.Error as error:
            logger.error("PROXIMITY: Insert en PROXIMITY fallado: {}.".format(error))
            #aqui tendríamos que llamar a acces_point.py para que volviera a ejecutarse
            llamada_access_point = True
            pass


logger.info("PROXIMITY: Numero de inserts realizados en la tabla USUARIOS: %d" %insertsUsers)
logger.info("PROXIMITY: Numero de inserts realizados en la tabla PROXIMITY: %d" % insertsProximity)


if connection.is_connected():
    cursor.close()
    connection.close()
    print("MySQL cerrado")

#tiempo transcurrido
elapsed_time = time() - start_time

if elapsed_time >= max_accepted_time:
    logger.warning("PROXIMITY: Tiempo de ejecucion: "+str(elapsed_time))
    sendTelegramMsg("La ejecución de "+nombreFichero+" ha tardado mas de "+max_accepted_time+" segundos, concretamente ha tardado: "+elapsed_time+" segundos.")
else:
    logger.info("PROXIMITY: Tiempo de ejecucion: "+str(elapsed_time))

if llamada_access_point:
    logger.warning("PROXIMITY: Access_point no identificado, llamada a access_point.py")
    exec(open('access_point.py').read())
    #exec(open('proximity.py').read())

print("################## FINAL PROXIMITY.PY ##################")
