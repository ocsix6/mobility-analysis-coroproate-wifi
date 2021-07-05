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

print("################## INCIO STATION.PY ##################")

#Inicio Query ALE
http = urllib3.PoolManager()
url = ALEUrlStation
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

if not os.path.isdir(dirJson + "/" + dirStation):
    os.mkdir(dirJson+"/"+dirStation)

#Guardamos fecha y hora actual para anadiselo al nombre del fichero
fechaActual=str(datetime.now().replace(microsecond=0))
nombreFichero="station_"+fechaActual+".json"
f = open(dirJson+"/"+dirStation+"/"+nombreFichero, "w")
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
dt_obtenidos = 0
insertsStation = 0
llamada_access_point = False
# Actualizamos la tabla USER
for x in datosJson["Station_result"]:
    if "device_type" not in x["msg"]:
        deviceType = default_device_type
    else:
        deviceType = x["msg"]["device_type"]


    mysqlSelect = "SELECT hashed_sta_eth_mac, device_type from USER WHERE hashed_sta_eth_mac=%s AND device_type=%s LIMIT 1"
    cursor.execute(mysqlSelect, (x["msg"]["hashed_sta_eth_mac"], default_device_type))
    records = cursor.fetchall()
    # solo entra aqui si el resultado del SELECT no es nulo y el devicetype es diferente del default
    if records and deviceType != default_device_type:
        sqlUpdate = """Update USER set device_type = %s where hashed_sta_eth_mac = %s """
        sqlParam = (deviceType, records[0][0],)
        cursor.execute(sqlUpdate, sqlParam)
        connection.commit()
        dt_obtenidos += cursor.rowcount

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

    if "role" not in x["msg"]:
        role=default_role
    else:
        role = x["msg"]["role"]

    if "hashed_sta_ip_address" not in x["msg"]:
        hashed_ip=default_hashed_ip
    else:
        hashed_ip=x["msg"]["hashed_sta_ip_address"]

    mysqlSelect = "SELECT date_time, hashed_sta_eth_mac, ap_name from STATION WHERE date_time=%s AND hashed_sta_eth_mac=%s AND ap_name=%s LIMIT 1"
    mysqlParams = (fecha,x["msg"]["hashed_sta_eth_mac"], x["msg"]["ap_name"],)
    cursor.execute(mysqlSelect, mysqlParams)
    records = cursor.fetchall()
    if not records:
        sqlInsert = """INSERT INTO STATION
                                    (date_time, hashed_sta_eth_mac, ap_name, role, bssid_addr, hashed_sta_ip_address) VALUES (%s, %s, %s, %s, %s, %s)"""
        insertvalues = (fecha,x["msg"]["hashed_sta_eth_mac"], x["msg"]["ap_name"], role,x["msg"]["bssid"]["addr"], hashed_ip)
        try:
            cursor.execute(sqlInsert, insertvalues)
            connection.commit()
            insertsStation += 1

        except mysql.connector.Error as error:
            logger.error("STATION: Insert en STATION fallado: {}.".format(error))
            #aqui tendríamos que llamar a acces_point.py para que volviera a ejecutarse
            llamada_access_point = True
            pass


logger.info("STATION: Numero de nuevos device_types obtenidos: " + str(dt_obtenidos))
logger.info("STATION: Numero de inserts realizados en la tabla USER: %d" %insertsUsers)
logger.info("STATION: Numero de inserts realizados en la tabla STATION: %d" % insertsStation)


if connection.is_connected():
    cursor.close()
    connection.close()
    print("MySQL cerrado")

#tiempo transcurrido
elapsed_time = time() - start_time

if elapsed_time >= max_accepted_time:
    logger.warning("STATION: Tiempo de ejecucion: "+str(elapsed_time))
    sendTelegramMsg("La ejecución de "+nombreFichero+" ha tardado mas de "+max_accepted_time+" segundos, concretamente ha tardado: "+elapsed_time+" segundos.")
else:
    logger.info("STATION: Tiempo de ejecucion: "+str(elapsed_time))

if llamada_access_point:
    logger.warning("STATION: Access_point no identificado, llamada a access_point.py")
    exec(open('access_point.py').read())
    #exec(open('station.py').read())

print("################## FINAL STATION.PY ##################")
