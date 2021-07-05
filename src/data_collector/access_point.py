import urllib3
import mysql.connector
from mysql.connector import Error
import json
from datetime import datetime
import os
from config import *
from ale_config import *

##
import logging.config
logging.config.fileConfig(os.getcwd() + '/logging.ini')
logger = logging.getLogger(__name__)
##
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


print("################## INCIO ACCESS_POINT.PY ##################")

http = urllib3.PoolManager()
url = ALEUrlAccessPoint
# pasamos el usuario y contrasena por headers
headers = urllib3.util.make_headers(basic_auth=ALEUser+':'+ALEPassword)
r = http.request('GET', url, headers=headers)

if r.status == 200:
    print("Query ALE realizada correctamente")
else:
    print("Problemas en Query ALE ")

# pasamos los datos a utf-8
datos = str(r.data, 'utf-8')
#Guardamos fecha y hora actual para anadiselo al nombre del fichero
if not os.path.isdir(dirJson):
    os.mkdir(dirJson)

if not os.path.isdir(dirJson + "/" + dirAccesPoint):
    os.mkdir(dirJson+"/"+dirAccesPoint)

fechaActual=str(datetime.now().replace(microsecond=0))
f = open(dirJson+"/"+dirAccesPoint+"/access_point_"+fechaActual+".json", "w")
f.write(datos)
f.close()

datosJson = json.loads(datos)

# Diccionarios para controlas los AP_GROUP y APs ya insertados anteriormente para no volverlos a intertar
apGroup = {}
ap = {}
# connexion a la base de datos

connection = mysql.connector.connect(
    host=BDHost,
    user=BDUser,
    passwd=BDPassword,
    port=BDPort,
    database=BDDatabase
)

cursor = connection.cursor()
# Feim la consulta
mysqlcode = "SELECT ap_group from AP_GROUP"
# Executam la consulta
cursor.execute(mysqlcode)
# Guardam el resultat de la consulta
records = cursor.fetchall()
logger.info("ACCES_POINT: Numero de AP_GROUP encontrados ya en la BD : "+str(cursor.rowcount))
# Per cada fila de la consulta, ficarem aquest valor al diccionari
for row in records:
    apGroup[row[0]] = "true"

mysqlcode = "SELECT ap_name, edificio_id from AP"
cursor.execute(mysqlcode)
records = cursor.fetchall()
logger.info("ACCESS_POINT: Numero de AP encontrados ya en la BD : "+str(cursor.rowcount))
for row in records:
     ap[row[0]] = "true"
     # si ese ap no tiene ningun edificio asignado
     if not row[1]:
         # cogemos el nombre del edificio con un split
         edifici = row[0].split("-", 2)[1]

         #metemos ese edificio en la tabla de edificios si no estaba ya
         sqlInsert = """INSERT IGNORE INTO EDIFICIO (id) VALUES (%s) """
         sqlParam = (edifici,)
         cursor.execute(sqlInsert, sqlParam)
         connection.commit()

         #con un update guardamos le añadimos el edificio
         sqlUpdate = """Update AP set edificio_id = %s where ap_name = %s """
         sqlParam = (edifici, row[0],)
         cursor.execute(sqlUpdate, sqlParam)
         connection.commit()

#Actualizamos la tabla AP_GROPUS
insertsApGroup=0
insertsAp = 0
for x in datosJson["Access_point_result"]:
    # Si este id no esta guardado anteriormente lo guardamos
    if x["msg"]["ap_group"] not in apGroup:
        # insert
        sqlInsert = """INSERT INTO AP_GROUP
                            (ap_group) VALUES (%s)"""
        insertvalues = (x["msg"]["ap_group"],)
        # Ahora que ya lo guardamos en la bd lo metemos en existentes
        apGroup[x["msg"]["ap_group"]] = "true"

        cursor.execute(sqlInsert, insertvalues)
        connection.commit()
        insertsApGroup+=1

    if x["msg"]["ap_name"] not in ap:
        # insert
        #cogemos el nombre del edificio
        edifici=x["msg"]["ap_name"].split("-", 2)[1]

        #insertamos ese edificio en la tabla EDIFICIO si no estaba antes
        sqlInsert = """INSERT IGNORE INTO EDIFICIO (id) VALUES (%s) """
        sqlParam = (edifici,)
        cursor.execute(sqlInsert, sqlParam)
        connection.commit()
        #

        sqlInsert = """INSERT INTO AP
                            (ap_name, ap_eth_mac_addr, ap_ip_address_af, ap_ip_address_addr, ap_group, edificio_id) VALUES (%s, %s, %s, %s, %s, %s)"""
        insertvalues = (x["msg"]["ap_name"],x["msg"]["ap_eth_mac"]["addr"],x["msg"]["ap_ip_address"]["af"], x["msg"]["ap_ip_address"]["addr"], x["msg"]["ap_group"],edifici,)
        # Ahora que ya lo guardamos en la bd lo metemos en existentes
        ap[x["msg"]["ap_name"]] = "true"

        cursor.execute(sqlInsert, insertvalues)
        connection.commit()
        insertsAp+=1

logger.info("ACCESS_POINT: Numero de inserts realizados en la tabla AP_GROUP: %d" %insertsApGroup)
logger.info("ACCESS_POINT: Numero de inserts realizados en la tabla AP: %d" % insertsAp)



if connection.is_connected():
    cursor.close()
    connection.close()
    print("MySQL cerrado")

print("################## FINAL ACCESS_POINT.PY ##################")
