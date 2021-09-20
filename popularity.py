# -*- coding: utf-8 -*-
"""
Created on Thu Dec 31 18:23:20 2020

@author: talgo
"""

import sys
import pandas as pd
import numpy as np
import zipfile as zp
import matplotlib.pyplot as plt
from ftplib import FTP
from io import StringIO
import mysql.connector as mysql
from datetime import datetime, date, time, timedelta
import time

## email functionality
import smtplib, ssl


### Connect to database
try:
    db = mysql.connect(host = "127.0.0.1",user = "user",passwd = "greek",database = "gtfs")
    db.ping() # raises an error if connection failed or does not exist
    cursor = db.cursor()
    print("Connection to the MySQL server has successfully established.")
except mysql.Error as e:
    print("Connection failed.\nThe error is: %s"%(e))
 
    
### Apply query
query =  """SELECT agency_id, line_id, number_of_trips_today, DENSE_RANK()OVER(PARTITION BY agency_id ORDER BY number_of_trips_today DESC) AS agency_popularity
                FROM   (SELECT agency_id,line_id, COUNT(*) AS number_of_trips_today
                		FROM routes JOIN (SELECT trip_id,trip_date,route_id FROM trips WHERE trip_date=DATE_ADD(CURDATE(), INTERVAL 0 DAY) ) AS trips 
                		ON routes.route_id=trips.route_id
                		GROUP BY agency_id,line_id) AS temp"""
cursor.execute(query)
data = cursor.fetchall() 

### Close connection

cursor.close()
db.close()

### Transform to Pandas

df = pd.DataFrame(data, columns=["agency_id","line_id","number_of_trips_today","agency_popularity"])

### Save the file
df.to_csv('popularity.csv',encoding='utf-8-sig')



