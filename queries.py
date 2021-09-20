# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io
import urllib, base64
from django.shortcuts import render
from django.http import HttpResponse
from django import forms
from django.db import connections
from datetime import datetime, date, time, timedelta


############################################################### Form queries ###########################################################

def max_date_for_forms():
  with connections['monitoring_warehouse'].cursor() as cursor: # query for retrieving the maximum date that is available with data
    query = """ SELECT date FROM date
                WHERE date_id=(SELECT MAX(DISTINCT date_id)
                                FROM stop_times); """
    cursor.execute(query)
  return str(cursor.fetchall()[0][0])

def min_date_for_forms():
  with connections['monitoring_warehouse'].cursor() as cursor: # query for retrieving the maximum date that is available with data
    query = """ SELECT date FROM date
                WHERE date_id=(SELECT MIN(DISTINCT date_id)
                                FROM stop_times); """
    cursor.execute(query)
  return str(cursor.fetchall()[0][0])

############################################################## End form queries ########################################################
#
#
#
############################################################# Report for line #########################################################

def base_trip_planning(line_number,direction,city):
  with connections['default'].cursor() as cursor: # query for base information about route: route_id, line_id, agency_id. allow us calculate other values with other queries.
    query ="""SELECT routes.route_id, line_id, agency_id
              FROM (SELECT r1.agency_id, r1.line_id, r1.route_id
                		FROM routes AS r1 JOIN trips AS t1 ON r1.route_id=t1.route_id
                		WHERE r1.line_number={} AND (direction={} OR direction=3)
                		GROUP BY r1.agency_id, r1.line_id, r1.route_id
                		HAVING COUNT(*)>= ALL(SELECT COUNT(*) AS number_trips
                              						FROM (SELECT * FROM routes WHERE direction={} OR direction=3) AS r2 JOIN trips AS t2 ON r2.route_id=t2.route_id
                              						WHERE r1.line_id=r2.line_id 
                              						GROUP BY r2.route_id) ) AS routes 
              JOIN trips AS trips ON routes.route_id=trips.route_id 
              JOIN stop_times AS st ON trips.trip_id=st.trip_id AND trips.trip_date=st.trip_date 
              JOIN (SELECT stop_id FROM stops WHERE stops.stop_desc LIKE '%{}%') AS stops ON st.stop_id=stops.stop_id
              LIMIT 1;""".format(line_number, direction, direction, city)
    cursor.execute(query)
  return cursor.description, cursor.fetchall()
  
  
def base_trip_planning_DW(line_number,direction,city):
  with connections['monitoring_warehouse'].cursor() as cursor: #query for base information about route: route_id, line_id, agency_id. allow us calculate other values with other queries.
    query ="""SELECT route_id,line_id,direction,agency_id
              FROM(
                (SELECT agency_id ,route_id,stop_id FROM stop_times) AS st1 
                JOIN (SELECT route_id,line_id,direction  FROM routes WHERE line_number={} AND direction={}) AS r USING(route_id)
                JOIN (SELECT stop_id FROM stops WHERE stop_city='{}') AS s USING (stop_id)
              )
              GROUP BY route_id,line_id,direction,agency_id
              ORDER BY COUNT(*) DESC
              LIMIT 1""".format(line_number, direction,city)
    cursor.execute(query)
  return cursor.description, cursor.fetchall()
  
  
def route_info(agency_id,line_id,direction,report_date):
  with connections['default'].cursor() as cursor: # query for all information about the route.
    query = """SELECT a.agency_id, a.agency_name, r.route_id, r.line_number, r.route_long_name, r.line_id, direction,alternative, t.trip_id,t.trip_date,stop_sequence,
                 departure_time,shape_dist_traveled,s.stop_id,stop_code,stop_name,stop_desc
              FROM (SELECT agency_id, agency_name FROM agency) AS a
              JOIN (SELECT agency_id, route_id, line_number,route_long_name, line_id,direction,alternative FROM routes WHERE agency_id={} AND line_id={} AND (direction={} OR direction=3 )) AS r ON a.agency_id=r.agency_id
              JOIN (SELECT trip_id,trip_date,trip_headsign,route_id FROM trips WHERE trip_date={}) AS t ON r.route_id=t.route_id
              JOIN (SELECT trip_id,trip_date,stop_sequence,stop_id,departure_time,shape_dist_traveled FROM stop_times WHERE trip_date={}) AS st 
                  ON st.trip_id=t.trip_id AND st.trip_date=t.trip_date
              JOIN (SELECT stop_id,stop_code,stop_name,stop_desc FROM stops) AS s ON st.stop_id=s.stop_id;""".format(agency_id,line_id,direction,report_date,report_date)
    cursor.execute(query)
  return cursor.description , cursor.fetchall()
  
  
def route_info_DW(line_id,direction,report_date):
  with connections['monitoring_warehouse'].cursor() as cursor: # query for all information about the route.
    query =  """SELECT a.agency_id, a.agency_name, r.route_id, r.line_number, r.route_long_name, r.line_id, direction,alternative, trip_id,d.date AS trip_date,stop_sequence, t.time AS departure_time, t1.time AS actual_time,time_difference, happend, actual_time_id, shape_dist_traveled,s.stop_id,stop_code,stop_name,stop_desc
                FROM (SELECT date_id,date FROM date WHERE date={}) AS d
                JOIN (SELECT agency_id ,route_id, departure_time_id, actual_time_id, stop_id ,date_id,trip_id,stop_sequence,shape_dist_traveled,time_difference,happend FROM stop_times) AS st ON d.date_id=st.date_id
                JOIN (SELECT route_id, line_number, line_id,direction,alternative,CONCAT(route_origin, '<->',route_destination ) AS route_long_name FROM routes WHERE line_id={} AND direction={}) AS r ON r.route_id=st.route_id
                JOIN (SELECT stop_id,stop_code,stop_name,stop_city AS stop_desc FROM stops) AS s ON st.stop_id=s.stop_id
                JOIN (SELECT agency_id,agency_name FROM agency) AS a ON st.agency_id=a.agency_id
                JOIN (SELECT time,time_id FROM time) AS t ON t.time_id=st.departure_time_id
                JOIN (SELECT time,time_id FROM time) AS t1 ON t1.time_id=st.actual_time_id;""".format(report_date, line_id, direction)
    cursor.execute(query)
  return cursor.description , cursor.fetchall()  
   
  
def route_directions(line_id):
  with connections['default'].cursor() as cursor: # query for all information about the route.
    query = """SELECT DISTINCT direction
               FROM routes
               WHERE line_id={};""".format(line_id)
    cursor.execute(query)
  return cursor.description , cursor.fetchall() 
  
  
def route_directions_DW(line_id):
  with connections['monitoring_warehouse'].cursor() as cursor: # query for all information about the route.
    query = """SELECT DISTINCT direction
               FROM routes
               WHERE line_id={};""".format(line_id)
    cursor.execute(query)
  return cursor.description , cursor.fetchall()   
  
  
def line_OTP(report_date, line_id,direction): 
  with connections['monitoring_warehouse'].cursor() as cursor:
    cursor.execute(
                      """SELECT SUM(happend) AS number_of_actual_trips
                FROM (SELECT date_id FROM date WHERE date={} ) AS d 
                JOIN (SELECT date_id,route_id,happend FROM stop_times WHERE stop_sequence=1 AND happend=1) AS st ON d.date_id=st.date_id 
                JOIN (SELECT route_id FROM routes WHERE line_id={} AND direction={}) AS r ON r.route_id=st.route_id;""".format(report_date, line_id,direction))
  return cursor.description , cursor.fetchall() 

def tripids_for_line_OTP(report_date, line_id,direction): 
  with connections['monitoring_warehouse'].cursor() as cursor:
    cursor.execute(
                      """SELECT trip_id
                FROM (SELECT date_id FROM date WHERE date={} ) AS d 
                JOIN (SELECT trip_id,date_id,route_id,happend FROM stop_times WHERE stop_sequence=1 AND happend=1) AS st ON d.date_id=st.date_id 
                JOIN (SELECT route_id FROM routes WHERE line_id={} AND direction={}) AS r ON r.route_id=st.route_id;""".format(report_date, line_id,direction))
  result = cursor.fetchall()
  if result:
    return pd.DataFrame(data=result, columns=['trip_id']).astype(str)['trip_id'].values.tolist() # return a list of trip_ids that happend
  else:
    return []
  
############################################################# End report for line #########################################################
#
#
#
############################################################# Report for station #########################################################

def routes_via_station(station , report_date): # query for information about the routes that go through station
  with connections['default'].cursor() as cursor:
    cursor.execute(
      """SELECT s.stop_id, s.stop_code, s.stop_name, s.stop_desc, st.stop_sequence, st.departure_time, t.trip_id, t.trip_date, t.trip_headsign,r.line_id  ,r.route_id, r.direction, r.line_number, r.route_long_name, r.alternative,  a.agency_id, a.agency_name
   FROM (SELECT * FROM stops WHERE stop_id=%s) AS s JOIN (SELECT trip_id, trip_date,stop_id,stop_sequence, departure_time FROM stop_times WHERE trip_date='%s' ) AS st ON s.stop_id=st.stop_id 
  	JOIN (SELECT trip_id, trip_date, trip_headsign, route_id FROM trips WHERE trip_date='%s') AS t ON st.trip_id=t.trip_id AND st.trip_date=t.trip_date
  	JOIN routes AS r ON t.route_id=r.route_id
    JOIN agency AS a ON r.agency_id=a.agency_id""" % (int(station), report_date, report_date) )
  return cursor.description , cursor.fetchall()  
  
  
def routes_via_station_DW(station , report_date): # query for information about the routes that go through station
  with connections['monitoring_warehouse'].cursor() as cursor:
    cursor.execute(
      """SELECT s.stop_id, s.stop_code, s.stop_name, s.stop_desc, st.stop_sequence, t.time as departure_time, t1.time as actual_time,trip_id, d.date as trip_date, trip_headsign,r.line_id  ,r.route_id, r.direction, r.line_number, r.route_long_name, r.alternative, a.agency_id, a.agency_name, origin_city
        FROM (SELECT date_id,date FROM date WHERE date='{}') AS d
        JOIN (SELECT agency_id ,route_id, departure_time_id,actual_time_id,stop_id ,date_id,trip_id,stop_sequence,shape_dist_traveled FROM stop_times) AS st ON d.date_id=st.date_id
        JOIN (SELECT route_id, line_number,direction, alternative,line_id, route_headsign AS trip_headsign,CONCAT(route_origin, '<->',route_destination ) AS route_long_name, origin_city  FROM routes) AS r ON r.route_id=st.route_id
        JOIN (SELECT stop_id,stop_code,stop_name,CONCAT(stop_street,", ",stop_city) AS stop_desc FROM stops WHERE stop_id='{}') AS s ON st.stop_id=s.stop_id
        JOIN (SELECT agency_id,agency_name FROM agency) AS a ON st.agency_id=a.agency_id
        JOIN (SELECT time,time_id FROM time) AS t ON t.time_id=st.departure_time_id
        JOIN (SELECT time,time_id FROM time) AS t1 ON t1.time_id=st.actual_time_id;""".format(report_date, station ) )
  return cursor.description , cursor.fetchall() 
 
 
   

############################################################# End report for station #########################################################
#
#
#
############################################################# Report for agency #########################################################

# Function that create list of all agencies in Database except trains and taxis. 
def list_of_agencies():
  with connections['default'].cursor() as cursor:
    cursor.execute("""SELECT agency_id, agency_name 
                      FROM agency
                      WHERE agency_id<>2 AND agency_id<>21 AND agency_id<52""")
  rows = cursor.fetchall()
  return rows
  
def list_of_agencies_DW():
  with connections['monitoring_warehouse'].cursor() as cursor:
    cursor.execute("""SELECT agency_id, agency_name 
                      FROM agency
                      WHERE agency_id<>2 AND agency_id<>21 AND agency_id<52""")
  rows = cursor.fetchall()
  return rows
  
  


def agency_info(agency_id, report_date): # today information about agency
  with connections['default'].cursor() as cursor:
    cursor.execute(
      """SELECT a.agency_id, agency_name, r.route_id, line_number, route_long_name, line_id, t.trip_id,t.trip_date, stop_sequence, s.stop_id, departure_time, shape_dist_traveled
         FROM (SELECT agency_id, agency_name FROM agency WHERE agency_id=%s) AS a JOIN routes AS r ON a.agency_id=r.agency_id
				 JOIN (SELECT * FROM trips WHERE trip_date='%s') AS t ON r.route_id=t.route_id
                JOIN (SELECT stop_id FROM stop_times WHERE trip_date='%s')  AS st ON t.trip_id=st.trip_id AND t.trip_date=st.trip_date
                JOIN stops AS s ON st.stop_id=s.stop_id;""" % (int(agency_id) , report_date, report_date) )
  return cursor.description , cursor.fetchall() 
  
  
def agency_info_DW(agency_id, report_date): # today information about agency
  with connections['monitoring_warehouse'].cursor() as cursor:
    cursor.execute(
   """SELECT a.agency_id, agency_name, r.route_id, line_number, route_long_name, line_id, st.trip_id,d.date as trip_date, stop_sequence, t.time as departure_time, t1.time AS actual_time,shape_dist_traveled
      FROM (SELECT date_id,date FROM date WHERE date='{}') AS d
      JOIN (SELECT agency_id ,route_id, departure_time_id,actual_time_id,stop_id ,date_id,trip_id,stop_sequence,shape_dist_traveled FROM stop_times) AS st ON d.date_id=st.date_id
      JOIN (SELECT route_id, line_number,direction, alternative,line_id, route_destination AS trip_headsign,CONCAT(route_origin,'<->',route_destination ) AS route_long_name FROM routes) AS r ON r.route_id=st.route_id
      JOIN (SELECT agency_id,agency_name FROM agency WHERE agency_id={}) AS a ON st.agency_id=a.agency_id
      JOIN (SELECT time,time_id FROM time) AS t ON t.time_id=st.departure_time_id
      JOIN (SELECT time,time_id FROM time) AS t1 ON t1.time_id=st.actual_time_id;""".format(report_date, int(agency_id) ) )
      # not necessary: JOIN (SELECT stop_id,stop_name_en as stop_name FROM stops) AS s ON st.stop_id=s.stop_id
  return cursor.description , cursor.fetchall()   
  
############################################################# End report for agency #########################################################


############################################################ Other Queries for Reports ######################################################


def most_popular_routes(current_date):
# Selected agencies: 3,5,15 most popular routes
  with connections['default'].cursor() as cursor:
    cursor.execute("""SELECT agency_name, line_number, route_long_name, num_of_trips,rank_five 
    FROM (SELECT *, RANK()OVER(PARTITION BY agency_id ORDER BY num_of_trips DESC) AS rank_five 
    FROM (SELECT a.agency_name, r.agency_id, r.line_id, r.line_number,MAX(r.route_long_name) AS route_long_name ,COUNT(*) AS num_of_trips 
    FROM agency AS a JOIN routes AS r ON a.agency_id=r.agency_id JOIN trips AS t ON r.route_id=t.route_id 
    WHERE t.trip_date = '%s' AND (a.agency_id=3 OR  a.agency_id=5 OR  a.agency_id=15) 
    GROUP BY r.agency_id, r.line_id,r.line_number) AS temp1) AS temp2 WHERE rank_five<6""" % (current_date))
  return cursor.fetchall()
    
  
'''  
def base_trip_planning(line_number,direction,city):
  with connection.cursor() as cursor: # query for base information about route: route_id, line_id, agency_id. allow us calculate other values with other queries.
    query = """SELECT  routes.route_id, line_id, agency_id
              FROM (SELECT r1.line_id, r1.route_id, r1.agency_id
                    FROM routes AS r1 JOIN trips AS t1 ON r1.route_id=t1.route_id
                    WHERE r1.line_number= {} AND (direction={} OR direction=3)
                    GROUP BY r1.line_id, r1.direction, r1.route_id
                    HAVING COUNT(*)>= (SELECT COUNT(*) AS number_trips
                  					FROM routes AS r2 JOIN trips AS t2 ON r2.route_id=t2.route_id
                  					WHERE r1.line_id=r2.line_id AND r1.direction=r2.direction
                  					GROUP BY r2.route_id
                  					ORDER BY number_trips DESC 
                  					LIMIT 1)  ) AS routes 
              JOIN trips ON routes.route_id=trips.route_id 
              JOIN stop_times AS st ON trips.trip_id=st.trip_id AND trips.trip_date=st.trip_date 
              JOIN (SELECT stop_id FROM stops WHERE stops.stop_desc LIKE '%{}%') AS stops ON st.stop_id=stops.stop_id
              LIMIT 1""".format(line_number,direction,city)
    cursor.execute(query)
  return cursor.fetchall() '''
  
  
def today_route_popularity_by_agency():
  with connections['default'].cursor() as cursor: # query for information about today popularity by his agency
    query =  """SELECT agency_id, line_id, number_of_trips_today, DENSE_RANK()OVER(PARTITION BY agency_id ORDER BY number_of_trips_today DESC) AS agency_popularity
                FROM   (SELECT agency_id,line_id, COUNT(*) AS number_of_trips_today
                		FROM routes JOIN (SELECT trip_id,trip_date,route_id FROM trips WHERE trip_date=DATE_ADD(CURDATE(), INTERVAL 0 DAY) ) AS trips 
                		ON routes.route_id=trips.route_id
                		GROUP BY agency_id,line_id) AS temp"""
    cursor.execute(query)
  return cursor.fetchall()
    

def working_intervals(report_date):
  with connections['SIRI'].cursor() as cursor: # query for defining the time intervals in which actual times were recorded
    query = """SELECT * FROM statistics WHERE response_date={}""".format(report_date)
    cursor.execute(query)
    df = pd.DataFrame(data=cursor.fetchall(),columns=[x[0] for x in cursor.description], dtype=str)
  
  if not df.empty:
    df['response_time'] = [pd.to_timedelta(str(x)) for x in df['response_time']]
    df['difference'] = [np.nan]+[df.iloc[i,3]-df.iloc[i-1,3] for i in range(1,df.shape[0])] # catch differences between response times
    max_dif = '600s' # define max difference for intervals decision - 10 minutes
    masking = (df['difference']>pd.to_timedelta(max_dif)).to_list() # catch all times where the differences was greater than max_dif

    i=0
    while(i<len(masking)):  # catch all times for the start and end of time intervals
      if masking[i]:        # start of interval
        masking[i+1] = True # end of interval
        i += 2              # increase the pointer by 2
      else:
        i+=1                # increase the pointer by 1 if start of interval isn't detected
    
    # load all intervals in a single list
    intervals = [min(df.response_time)]+df[masking]['response_time'].to_list()+[max(df.response_time)]

    # return the calculated the final time intervals in which the actual times were being recorded
    return [(intervals[i],intervals[i+1]) for i in range(0,len(intervals),2)]
  else:
    return [(pd.to_timedelta('00:00:00'),pd.to_timedelta('00:00:01'))] # return dummy working interval in case response times from the statistics table weren't found for the chosen report date
    