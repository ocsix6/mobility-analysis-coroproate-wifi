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

print("################## INCIO PRESENCE.PY ##################")

#Inicio Query ALE
http = urllib3.PoolManager()
url = ALEUrlPresence
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

if not os.path.isdir(dirJson + "/" + dirPresence):
    os.mkdir(dirJson+"/"+dirPresence)

#Guardamos fecha y hora actual para anadiselo al nombre del fichero
fechaActual=str(datetime.now().replace(microsecond=0))
nombreFichero="presence_"+fechaActual+".json"
f = open(dirJson+"/"+dirPresence+"/"+nombreFichero, "w")
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

insertsUsers=0
insertsPresence = 0
llamada_access_point = False
for x in datosJson["Presence_result"]:

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

    if "hashed_sta_ip_address" not in x["msg"]:
        hashed_ip=default_hashed_ip
    else:
        hashed_ip=x["msg"]["hashed_sta_ip_address"]

    mysqlSelect = "SELECT date_time, hashed_sta_eth_mac, ap_name from PRESENCE WHERE date_time=%s AND hashed_sta_eth_mac=%s AND ap_name=%s LIMIT 1"
    mysqlParams = (fecha,x["msg"]["hashed_sta_eth_mac"], x["msg"]["ap_name"],)
    cursor.execute(mysqlSelect, mysqlParams)
    records = cursor.fetchall()
    if not records:
        sqlInsert = """INSERT INTO PRESENCE
                                    (date_time, hashed_sta_eth_mac, ap_name, hashed_sta_ip_address) VALUES (%s, %s, %s, %s)"""
        insertvalues = (fecha, x["msg"]["hashed_sta_eth_mac"], x["msg"]["ap_name"], hashed_ip)
        try:
            cursor.execute(sqlInsert, insertvalues)
            connection.commit()
            insertsPresence += 1

        except mysql.connector.Error as error:
            #print(x["msg"]["ap_name"])
            logger.error("PRESENCE: Insert en PRESENCE fallado: {}.".format(error))
            #aqui tendriamos que llamar a acces_point.py para que volviera a ejecutarse
            llamada_access_point = True
            pass


logger.info("PRESENCE: Numero de inserts realizados en la tabla USERS: %d" % insertsUsers)
logger.info("PRESENCE: Numero de inserts realizados en la tabla PRESENCE: %d" % insertsPresence)

if connection.is_connected():
    cursor.close()
    connection.close()
    print("MySQL cerrado")

#tiempo transcurrido
elapsed_time = time() - start_time

if elapsed_time >= max_accepted_time:
    logger.warning("PRESENCE: Tiempo de ejecucion: "+str(elapsed_time))
    sendTelegramMsg("La ejecución de "+nombreFichero+" ha tardado mas de "+max_accepted_time+" segundos, concretamente ha tardado: "+elapsed_time+" segundos.")
else:
    logger.info("PRESENCE: Tiempo de ejecucion: "+str(elapsed_time))

if llamada_access_point:
    logger.warning("PRESENCE: Access_point no identificado, llamada a access_point.py")
    exec(open('access_point.py').read())
    #exec(open('presence.py').read())

print("################## FINAL PRESENCE.PY ##################")
