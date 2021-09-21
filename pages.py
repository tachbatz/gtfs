import numpy as np
import pandas as pd
import sys
import matplotlib.pyplot as plt
import io
import urllib, base64
import plotly.graph_objects as go,plotly.express as px # interactive graph plotting

from django.shortcuts import render
from django.http import HttpResponse
from django import forms
from django.db import connections
from datetime import datetime, date, time, timedelta
from gtfs.queries import *
import time
current_date = date.today()


############################################################# Report for line #########################################################

# Function that calculate values for route and return them back to line_report at views.py 
def reports_for_line(line_id, city, direction, report_date, lang):

  values_to_render = {} # dict for render the values to bus_line_page.html

  time_initiate = time.time() # for peformance analysis purpose

  #base_trip_planning_column, base_trip_planning_rows = base_trip_planning_DW(line_number,direction,city)   # function with query for information about the base trip planning
  #base_trip_planning_column = [ x[0] for x in base_trip_planning_column ] # column name appear at index 0 at corsur.description
  
  

  #base_trip_planning_data = pd.DataFrame( base_trip_planning_rows , columns=base_trip_planning_column ) # create DataFrame based on select columns from the query
  
  #return values_to_render

  #route_id = base_trip_planning_data['route_id'].iloc[0]
  #line_id = base_trip_planning_data['line_id'].iloc[0]
  #agency_id = base_trip_planning_data['agency_id'].iloc[0]

  column, rows = route_info_DW(line_id,direction, report_date) # function with query about today schedule of agency
  column = [ x[0] for x in column ] # column name appear at index 0 at cursor.description

  values_to_render['trip_planning_query_time'] = round(time.time()-time_initiate,3) # the time the query took in seconds
  data = pd.DataFrame( rows , columns=column ) 
  # data columns: "agency_id", "agency_name", "route_id", "line_number", "route_long_name", "line_id" , "direction","alternative" ,"trip_id" ,"trip_date","stop_sequence", "departure_time","actual_time","shape_dist_traveled","stop_id","stop_code","stop_name","stop_desc", "time_difference", "happend", "actual_time_id"
  
  if data.empty: # in case no data was returned
    return False # stop the calculations
  
  agency_name = data['agency_name'].iloc[0]
  values_to_render['agency_name'] = agency_name # add value to dictionary.
  agency_id = data['agency_id'].iloc[0] 
  values_to_render['direction'] = direction # add value to dictionary.
  
  # For CSV export
  values_to_render['data'] = data.sort_values(by=['direction','trip_id','stop_sequence'])
  
  # find main route
  main_route = data[['route_id', 'trip_id','stop_sequence']]
  main_route = main_route[ main_route['stop_sequence'] == 1 ]
  main_route = main_route[ ['route_id', 'trip_id'] ]
  main_route = main_route.groupby(by=['route_id'] ,as_index=False).count()
  main_route = main_route.sort_values(by=['trip_id'] ,ascending=True)
  route_id = main_route['route_id'].iloc[-1]
  
  line_number_data = data[ data['route_id']==route_id ]
  line_number = line_number_data['line_number'].iloc[0]
  values_to_render['line_number'] = line_number
  
  # create string to describe route derection by start and last stations.
  route_name = data[ (data['line_id']== line_id) & (data['route_id']==route_id) & (data['direction']==direction ) ]
  alt_choosen = route_name['alternative'].iloc[0]
  alt_route_name = route_name['route_long_name'].iloc[0]
  route_name = route_name['route_long_name'].iloc[0]
  index = route_name.find("<->") 
  route_from = route_name[0:index] # split route_name by "<->".
  route_to = route_name[index+3:] # split route_name by "<->".
  values_to_render['route_name']= [route_from, route_to] #add value to dictionary.
  
  # alternative for route
  alternatives = data[ ( data['direction']==direction )  & (data['alternative'] != '0' ) & (data['alternative'] != '#' ) ]
  alternatives = alternatives[ alternatives['route_long_name'] != alt_route_name ]
  #alternatives = alternatives[ alternatives['route_long_name'].apply( lambda x: city in x[:x.find("<->")] ) ]
  alternatives = alternatives[ 'route_long_name' ].drop_duplicates()
  alternatives = alternatives.tolist()
  temp = []
  for i in range(len(alternatives)):
    temp.append([alternatives[i], i+1])
 
  values_to_render['alternatives'] = temp
  if len(temp)>0:
    values_to_render['alternative_flag'] = 1
  else:
    values_to_render['alternative_flag'] = 0

  trip_data = data[ (data['line_id']== line_id) & (data['route_id']==route_id) & (data['direction']==direction ) ] # df about main route
  trip_id= trip_data['trip_id'].iloc[0] # choose trip_id of routes's trips.
  trip_date = trip_data['trip_date'].iloc[0] # choose trip_date of routes's trips.
  trip_data = trip_data[ (trip_data['trip_date']== trip_date) & (trip_data['trip_id']==trip_id) ] # df about trip of main route.
  trip_data = trip_data[ ['stop_sequence' , 'stop_name', 'stop_id', 'stop_code', 'departure_time','shape_dist_traveled', 'stop_desc'] ].sort_values(by=['stop_sequence']) # sort row by number of station from 1 to N.
  list_trip_stations = trip_data[ ['stop_sequence' , 'stop_name', 'stop_code', 'stop_id'] ].values.tolist() # list of route's stations
  values_to_render['list_trip_stations'] = list_trip_stations #add value to dictionary.
  trip_departure_time = trip_data[ 'departure_time' ].values.tolist() 
  first_departure_time = trip_departure_time[0] # general first departure time.
  last_departure_time = trip_departure_time[-1] # general last departure time, to calculate estimated travel time.
  hour,minute = time_length( first_departure_time, last_departure_time)
  values_to_render['estimated_travel_time'] = [hour , minute] #add value to dictionary.
  values_to_render['today_date'] = trip_date #add value to dictionary.
  

  # Calculate the average distance between stops
  distance_list = trip_data[ 'shape_dist_traveled' ].values.tolist()
  average_distance_between_stops = np.average([distance_list[i+1]-distance_list[i] for i in range(len(distance_list)-1)]) # average length between stops.
  #average_distance_between_stops = describe_distance( average_distance_between_stops ) # string describe length between stops, we stop using this function due to HE/EN versions.
  average_distance_between_stops = round( average_distance_between_stops/1000, 2) 
  values_to_render['average_distance_between_stops'] = average_distance_between_stops #add value to dictionary.
  
  # Calculate the Estimated avarage speed (KMH)
  start_time=str( first_departure_time )
  start_time=60*int(start_time[:2])+int(start_time[3:5]) # calculate start time. 
  finish_time=str( last_departure_time )
  finish_time=60*int(finish_time[:2])+int(finish_time[3:5]) # calculate end time.
  estimated_avarage_speed = int( round( (distance_list[-1]/1000)/((finish_time-start_time)/60) , 0)) # calculate speet from formula of Speed*Time=Length.
  values_to_render['estimated_avarage_speed'] = estimated_avarage_speed  #add value to dictionary. 
    
  
  # cities that the bus trip goes through them
  trip_cities=trip_data[ 'stop_desc' ].values.tolist()
  cities=[]
  if trip_cities[0].find("עיר:")>-1:
    for line in trip_cities:
      cities.append(line[line.find("עיר:")+5 : line.find("רציף:")-1]) # get city name from stop_desc string.
    trip_cities = list(dict.fromkeys(cities)) # remove duplicate
  else:
    trip_cities=trip_data[ 'stop_desc' ].drop_duplicates().values.tolist()
  trip_city=""
  for x in trip_cities: # create one string with all cities names.
    trip_city+=x+", "
  trip_city=trip_city[0:-2] # remove last 2 chars ", ".
  values_to_render['trip_city'] = trip_city #add value to dictionary.

  
  # Length of trip
  #length_travel = describe_distance(distance_list[-1]) # function to describe length as string. we stop using this function due to HE/EN versions.
  length_travel = round(distance_list[-1]/1000, 2)
  values_to_render['length_travel'] = length_travel #add value to dictionary.
  
  # calculate MIN and MAX distance between stations
  min_distance , max_distance = min_and_max_difference_between_station(distance_list) # function to calculate the min and max distance between stops.
  values_to_render['min_distance'] =  round(min_distance/1000, 2) #add value to dictionary.
  values_to_render['max_distance'] = round(max_distance/1000, 2) #add value to dictionary.
  
  # Line schedule for today
  today_schedule = data[ (data['line_id']== line_id) & (data['stop_sequence']==1) & (data['direction']==direction ) ].sort_values(by=['departure_time'])

  consider_as_OT = (-300,300) # interval of seconds to consider a trip as on-time
  
  OTP_calc = [[], []]
  for triptime in today_schedule[today_schedule['happend']==1]['time_difference']: # for each recorded trip
    if triptime >= consider_as_OT[0] and triptime <= consider_as_OT[1]: # is time difference between the interval
      OTP_calc[0].append(1)
    else:
      OTP_calc[1].append(1)
  
  OTP_calc = [np.sum(OTP_calc[0]), np.sum(OTP_calc[1])] # recorded on time trips and recorded not on time trips

  if OTP_calc[0] or OTP_calc[1]: # if we have values for on-time or not on-time trips
    values_to_render['OTP_calc'] = OTP_calc
    values_to_render['OTP_measure'] = "{0:.2f}%".format((OTP_calc[0]/len(today_schedule[today_schedule['happend']==1]['time_difference'])*100))
  else:
    values_to_render['OTP_calc'] = ['--','--']
    values_to_render['OTP_measure'] = "--"
    

  today_schedule_times = today_schedule['departure_time'].values.tolist()
  today_schedule = today_schedule[['departure_time','trip_id','time_difference']].astype(str)
  today_schedule['time_difference'] = [x.replace(".0","") for x in today_schedule['time_difference']] # avoiding .0 at the end, leading to a failure during conversion to int
  today_schedule = today_schedule.astype(str).values.tolist()
  today_schedule_times_and_tripids, time_differences = today_departure_times(today_schedule) #add value to a temporary list first, we will update it later with Recorded Trips that happend.
  
  values_to_render['time_differences'] = time_differences

  # Line frequency for today
  hour,minute = frequency(today_schedule_times) # function to calculate frequency, return string describe frequency.
  values_to_render['today_frequency'] = [hour,minute] #add value to dictionary.
  first_trip = today_schedule_times[0][:5] # first trip for today.
  values_to_render['first_trip'] = first_trip #add value to dictionary.
  last_trip = today_schedule_times[-1][:5] # last trip for today.
  values_to_render['last_trip'] = last_trip #add value to dictionary.
  number_trip_today = len(today_schedule_times) # number of trips for today.
  values_to_render['number_trip_today'] = number_trip_today #add value to dictionary.
  
  # calculte today popularity
  # New function will calculte the popularity, for now it's -1.
  popularity = pd.read_csv('/var/www/mysite/gtfs/popularity.csv')
  popularity = popularity[ (popularity['agency_id']==agency_id) & (popularity['line_id']== line_id)] # get the popularity of the choosen route.
  values_to_render['today_popularity_among_his_agency'] = popularity['agency_popularity'].iloc[0] if not popularity['agency_popularity'].empty else "N/A" #add value to dictionary.

  hours=["04 - 06", "06 - 08", "08 - 10", "10 - 12" , "12 - 14",
         "14 - 16", "16 - 18" , "18 - 20" , "20 - 22", "22 - 24", "24 - 28"] # histogram hours ranges.

  title = 'Number of Trips, Divided Into Hour Ranges' if lang=='en' else 'כמות הנסיעות שהקו מבצע, בחלוקה לטווחי שעות'
  y_title = 'Number of Trips' if lang=='en' else 'מספר נסיעות'
  x_title = 'Hour Range' if lang=='en' else 'טווחי שעות'

  # picture = histogram_picture(hours,histogram_list_trip_per_hours(today_schedule_times),x_axis,y_axis,title) # histogram picture of route departure for today
  # values_to_render['today_schedule_picture'] = picture #add value to dictionary.

  interactive_graph = histogram_plotly(hours, histogram_list_trip_per_hours(today_schedule_times), x_title, y_title, title)
  values_to_render['interactive_graph'] = interactive_graph
  
  # directions of route
  
  column_route_directions, rows_route_directions = route_directions_DW(line_id) # function with query about route's directions.
  column_route_directions = [ x[0] for x in column_route_directions ] # column name appear at index 0 at corsur.description
  data_route_directions = pd.DataFrame( rows_route_directions , columns=column_route_directions )
  values_to_render['directions'] = data_route_directions['direction'].values.tolist()
  
  time_initiate = time.time()                                                           # catch the time before queries begin

  column_line_OTP, rows_line_OTP = line_OTP(report_date, line_id,direction)
  actual_trip_ids = tripids_for_line_OTP(report_date, line_id,direction)                # a list of the trip_ids that actually happend
  unknown_trip_ids = unknown_trips_check(report_date,today_schedule_times_and_tripids)  # list all trips that we don't know they happend

  values_to_render['query_time_OTP'] = round(time.time()-time_initiate,3)               # the time the query took in seconds



  for i in range(len(today_schedule_times_and_tripids)):
    for j in range(len(today_schedule_times_and_tripids[i])):
      if str(today_schedule_times_and_tripids[i][j][1]) in actual_trip_ids:
        today_schedule_times_and_tripids[i][j][1] = "✅"    # mark this trip as happend
      elif str(today_schedule_times_and_tripids[i][j][1]) in unknown_trip_ids:
        today_schedule_times_and_tripids[i][j][1] = "�"     # mark this trip as unknown
      else:
        today_schedule_times_and_tripids[i][j][1] = "❌"    # mark this trip as not happend

  values_to_render['today_departure_times'] = today_schedule_times_and_tripids

  column_line_OTP = [ x[0] for x in column_line_OTP ]                     # column name appear at index 0 at cursor.description
  data_line_OTP = pd.DataFrame( rows_line_OTP , columns=column_line_OTP ) # create DataFrame from column and SQL query table.
  if data_line_OTP['number_of_actual_trips'].iloc[0] is None:
    values_to_render['number_of_actual_trips'] = 0
  else:
    values_to_render['number_of_actual_trips'] = data_line_OTP['number_of_actual_trips'].iloc[0]
  
  values_to_render['number_of_unknown_trips'] = len(unknown_trip_ids)
  values_to_render['number_of_missed_trips'] = number_trip_today - values_to_render['number_of_actual_trips'] - values_to_render['number_of_unknown_trips']
  prec_of_actual_trips = int(100*values_to_render['number_of_actual_trips']/number_trip_today)
  prec_of_missed_trips = int(100*values_to_render['number_of_missed_trips']/number_trip_today)
  prec_of_unknown_trips = int(100*values_to_render['number_of_unknown_trips']/number_trip_today)

  if lang=='en': # if the currently used language is English
    title = 'Trips'
    group_title = 'Classification'
    number_title = 'Number of trips'
    if values_to_render['number_of_unknown_trips'] == 0:
      labels = 'Recorded Trips','Unrecorded Trips'
      sizes = [ prec_of_actual_trips , prec_of_missed_trips ]
      numbers = [values_to_render['number_of_actual_trips'], values_to_render['number_of_missed_trips']]
    elif prec_of_unknown_trips == 100:
      labels = 'Unknown Trips',
      sizes = [ prec_of_unknown_trips ]
      numbers = [values_to_render['number_of_unknown_trips']]
    else:
      labels = 'Recorded Trips','Unrecorded Trips','Unknown Trips'
      sizes = [ prec_of_actual_trips , prec_of_missed_trips, prec_of_unknown_trips]
      numbers = [values_to_render['number_of_actual_trips'], values_to_render['number_of_missed_trips'], values_to_render['number_of_unknown_trips']]
  else:
    title = 'נסיעות'
    group_title = '\nסיווג'
    number_title = '\nמספר נסיעות'
    if values_to_render['number_of_unknown_trips'] == 0:
      labels = 'נסיעות-מתועדות', 'נסיעות-לא-מתועדות'
      sizes = [ prec_of_actual_trips , prec_of_missed_trips ]
      numbers = [values_to_render['number_of_actual_trips'], values_to_render['number_of_missed_trips']]
    elif prec_of_unknown_trips == 100:
      labels = 'נסיעות-לא-ידועות'
      sizes = [ prec_of_unknown_trips ]
      numbers = [values_to_render['number_of_unknown_trips']]
    else:
      labels = 'נסיעות-מתועדות', 'נסיעות-לא-מתועדות', 'נסיעות-לא-ידועות'
      sizes = [ prec_of_actual_trips , prec_of_missed_trips, prec_of_unknown_trips]
      numbers = [values_to_render['number_of_actual_trips'], values_to_render['number_of_missed_trips'], values_to_render['number_of_unknown_trips']]


  # values_to_render['actual_and_missed_trips_picture'] = pie_chart(labels,sizes,3)
  values_to_render['interactive_actual_and_missed_trips_pie_chart'] = pie_plotly(numbers, labels, group_title, number_title, title)


  return values_to_render

####################################################### End report for line  ###############################################################################



    
############################################## Report for station ######################################################################    
    
def reports_for_station(station , report_date, lang):

  values_to_render = {} # dictinary with values to render on html page

  time_initiate = time.time()

  column, rows = routes_via_station_DW(station , report_date) # function with query about the routes that go through station

  values_to_render['query_time'] = round(time.time()-time_initiate,3) # the time the query took in seconds

  column = [ x[0] for x in column ] # column name appear at index 0 at corsur.description
  data = pd.DataFrame( rows , columns=column ) # create DataFrame based on select columns from the query
  #data columns: 'stop_id', 'stop_code', 'stop_name', 'stop_desc', 'stop_sequence', 'departure_time', 'actual_time' ,'trip_id', 'trip_date', 'trip_headsign', 'line_id','route_id', 'direction', 'line_number', 'route_long_name', 'alternative' ,'agency_id', 'agency_name'
  
  if data.empty: # in case no data was returned
    return False # stop the calculations

  #values_to_render['data'] = data

  data = data.sort_values(by=['departure_time']) # order by departure_time, ASC order
  values_to_render['stop_name'] = data['stop_name'].iloc[0]  #add value to dictionary.
  values_to_render['stop_adress'] = data['stop_desc'].iloc[0]  #add value to dictionary.
  values_to_render['first_arrival'] = data['departure_time'].iloc[0]  #add value to dictionary.
  values_to_render['last_arrival'] = data['departure_time'].iloc[-1]  #add value to dictionary.
  values_to_render['stop_code'] = data['stop_code'].iloc[0]  #add value to dictionary.
  
  data_trips_per_route=data[['line_id','line_number', 'agency_name','trip_id', 'trip_date', 'direction', 'origin_city']]
  data_trips_per_route=data_trips_per_route.groupby(['line_id','line_number', 'agency_name', 'direction', 'origin_city'], as_index=False).count() # calculate the number of trips per route
  #data_main_routes=data[ (data['alternative']== '#') | (data['alternative']=='0')  ] # take only the main routes
  data_main_routes = data[['trip_headsign','line_id', 'direction', 'route_long_name']]  
  data_main_routes=data_main_routes.drop_duplicates() # remove duplicate.
  data_trips_per_route.reset_index(drop=True, inplace=True)
  data_main_routes.reset_index(drop=True, inplace=True)
  routes_table=pd.merge(data_trips_per_route,data_main_routes,on=['line_id','direction'],how='inner') # inner join of 2 DataFrame by ['line_id','direction'] columns
  routes_table=routes_table.sort_values(by=['line_number'])
  routes_table=routes_table.drop(columns=['trip_date'])
  routes_table['city'] = routes_table['route_long_name'].apply(lambda x: x[x.find("-")+1:x.find("<->")]) # find city name.
  routes_table['route_origin'] = routes_table['route_long_name'].apply(lambda x: x[:x.find("<->")])  #change route_long_name string. add value to dictionary.
  routes_table['route_destination'] = routes_table['route_long_name'].apply(lambda x: x[x.find("<->")+3:])
  routes_table.drop(['route_long_name','origin_city'],axis=1,inplace=True)
  

  # drop duplicates
  routes_table_to_render = routes_table.drop_duplicates(subset=['line_id', 'line_number', 'agency_name', 'direction']) # make sure each line appear only once
  routes_table_to_render = routes_table_to_render.values.tolist()
  values_to_render['routes_table'] = routes_table_to_render #add value to dictionary.
  
  ############## create histogram of trips per hour
  times=data['departure_time'].values.tolist()
  hours=["04 - 06", "06 - 08", "08 - 10", "10 - 12" , "12 - 14", "14 - 16",
   "16 - 18" , "18 - 20" , "20 - 22", "22 - 24", "24 - 28"] # hours ranges.

  title = 'Number of Trips in Station, Divided Into Hour Ranges' if lang=='en' else 'כמות הנסיעות שעוברות בתחנה, בחלוקה לטווחי שעות'
  y_title = 'Number of Trips' if lang=='en' else 'מספר-נסיעות\n'
  x_title = 'Hour Range' if lang=='en' else 'טווחי-שעות\n'

  values_to_render['histogram_hours_interactive_graph'] = histogram_plotly(hours, histogram_list_trip_per_hours(times), x_title, y_title, title)
  # values_to_render['histogram_hours'] = histogram_picture( hours, histogram_list_trip_per_hours(times) , x_axis, y_axis , title, 2) # create histogram picture
  
  ############### create histogram of trips per agency
  df4=data[['agency_name','trip_id','trip_date']]
  df4=df4.groupby(['agency_name'], as_index=False).count() 
  df4=df4[['agency_name','trip_id']]  
  agency=df4['agency_name'].values.tolist()
  agency = [ x[::-1] for x in agency ] # reverse string because of hebrew alphabet
  agency_in_order = [ x[::-1] for x in agency]
  values=df4['trip_id'].values.tolist()

  title = 'Number of Trips in Station, per Agency' if lang=='en' else 'כמות הנסיעות שעוברות בתחנה, בחלוקה לפי מפעילים'
  y_title = 'Number of Trips' if lang=='en' else 'מספר-נסיעות\n'
  x_title = 'Agency Name' if lang=='en' else 'שם-מפעיל\n'

  # uri2=histogram_plotly(agency, values, x_axis, y_axis, title, 3)
  # values_to_render['histogram_agencies'] = uri2 #add value to dictionary.

  values_to_render['histogram_agencies_interactive'] = histogram_plotly(agency_in_order, values, x_title, y_title, title)

  values_to_render['data'] = data
  
  return values_to_render

####################################### End report for station ####################################################################

 
  
 ######################################################## Report for agency ###############################################################
 
def reports_for_agency(agency,report_date,lang):
  values_to_render={}
  values_to_render['agency_id'] = agency

  time_initiate = time.time() # for performance evaluation purposes

  column, rows = agency_info_DW(agency,report_date)

  values_to_render['query_time'] = round(time.time()-time_initiate,3) # the time the query took in seconds

  column = [ x[0] for x in column ] # column name appear at index 0 at corsur.description
  data = pd.DataFrame( rows , columns=column ) # create DataFrame from column and SQL query table.
  # data columns: agency_id, agency_name, route_id, line_number, route_long_name, line_id, trip_id,trip_date, stop_sequence, stop_id, departure_time, shape_dist_traveled
  
  
  if data.empty: # in case no data was returned
    return False # stop the calculations

  values_to_render['data'] = data

  values_to_render['agency_name'] = data['agency_name'].iloc[0]
  # find lowest line by number of stations
  rank_by_station = data[['trip_id','trip_date', 'stop_sequence','route_long_name']]
  rank_by_station = rank_by_station.groupby(['trip_id','trip_date'] ,as_index=False).count()
  rank_by_station = rank_by_station.sort_values(by=['stop_sequence'] ,ascending=True)
  lowest_id = rank_by_station['trip_id'].iloc[0]
  lowest_date = rank_by_station['trip_date'].iloc[0]
  lowest_number_station = rank_by_station['stop_sequence'].iloc[0]
  lowest_by_station_data = data[(data['trip_id'] == lowest_id) & (data['trip_date'] == lowest_date)]
  lowest_name_route_by_station = lowest_by_station_data['route_long_name'].iloc[0].split('<->')  
  lowest_line_number_by_station =  lowest_by_station_data['line_number'].iloc[0]
  values_to_render['lowest_number_station'] = lowest_number_station                       # number of station
  values_to_render['lowest_name_route_by_station'] = lowest_name_route_by_station         # line name with least number of station
  values_to_render['lowest_line_number_by_station'] = lowest_line_number_by_station       # line number with least number of station
  
  
  # find highest line by number of stations
  rank_by_station = data[['trip_id','trip_date', 'stop_sequence','route_long_name']]
  rank_by_station = rank_by_station.groupby(['trip_id','trip_date'] ,as_index=False).count()
  rank_by_station = rank_by_station.sort_values(by=['stop_sequence'] ,ascending=True)
  highest_id = rank_by_station['trip_id'].iloc[-1]
  highest_date = rank_by_station['trip_date'].iloc[-1]
  highest_number_station = rank_by_station['stop_sequence'].iloc[-1]
  highest_by_station_data = data[(data['trip_id'] == highest_id) & (data['trip_date'] == highest_date)]
  highest_name_route_by_station = highest_by_station_data['route_long_name'].iloc[0].split('<->')  
  highest_line_number_by_station =  highest_by_station_data['line_number'].iloc[0]
  values_to_render['highest_number_station'] = highest_number_station                      # number of station
  values_to_render['highest_name_route_by_station'] = highest_name_route_by_station        # line name with most number of station
  values_to_render['highest_line_number_by_station'] = highest_line_number_by_station      # line number with most number of station
  
  # find the fastest and lowest lines
  rank_by_time = data[['trip_id','trip_date', 'departure_time']]
  min_departure_time = rank_by_time.groupby(['trip_id','trip_date']).agg({'departure_time':'min'}).reset_index()
  min_departure_time = min_departure_time.rename(columns={"departure_time": "min_departure_time"})  # get the finish time for a single trip
  max_departure_time = rank_by_time.groupby(['trip_id','trip_date']).agg({'departure_time':'max'}).reset_index()
  max_departure_time = max_departure_time.rename(columns={"departure_time": "max_departure_time"})   # get the start time for a single trip
  time_data = pd.merge(min_departure_time, max_departure_time ,on=['trip_id','trip_date'],how='inner') # one dataframe that include start time and finish time at different columns.
  time_data['gap'] = time_data['max_departure_time'].apply(lambda x: int(x[0:2])*3600+int(x[3:5])*60+int(x[6:]))-time_data['min_departure_time'].apply(lambda x: int(x[0:2])*3600+int(x[3:5])*60+int(x[6:]))  # calculate the difference between start and finish.
  time_data = time_data.sort_values(by=['gap'] ,ascending=True) # data frame of travel lenght time from shortest to longest
  
  # lowest line
  slowest_id = time_data['trip_id'].iloc[-1]
  slowest_date = time_data['trip_date'].iloc[-1]
  slowest_route_time = int(time_data['gap'].iloc[-1]/60)  # time by minutes
  values_to_render['slowest_route_time'] = slowest_route_time  # add slowest time to dictionary
  slowest_route_name_time = data[(data['trip_id'] == slowest_id) & (data['trip_date'] == slowest_date)]
  slowest_route_name_time = slowest_route_name_time['route_long_name'].iloc[0].split('<->')
  values_to_render['slowest_route_name_time'] = slowest_route_name_time  # add slowest line name to dictionary
  slowest_line_number_time = data[(data['trip_id'] == slowest_id) & (data['trip_date'] == slowest_date)]
  slowest_line_number_time = slowest_line_number_time['line_number'].iloc[0]
  values_to_render['slowest_line_number_time'] = slowest_line_number_time  # add fastest line number to dictionary
  
  # fastest line
  fastest_id = time_data['trip_id'].iloc[0]
  fastest_date = time_data['trip_date'].iloc[0]
  fastest_route_time = int(time_data['gap'].iloc[0]/60)  # time by minutes
  values_to_render['fastest_route_time'] = fastest_route_time  # add fastest time to dictionary
  fastest_route_name_time = data[(data['trip_id'] == fastest_id) & (data['trip_date'] == fastest_date)]
  fastest_route_name_time = fastest_route_name_time['route_long_name'].iloc[0].split('<->')
  values_to_render['fastest_route_name_time'] = fastest_route_name_time  # add fastest line name to dictionary
  fastest_line_number_time = data[(data['trip_id'] == fastest_id) & (data['trip_date'] == fastest_date)]
  fastest_line_number_time = fastest_line_number_time['line_number'].iloc[0] 
  values_to_render['fastest_line_number_time'] = fastest_line_number_time # add slowest line number to dictionary
  
  
  # number of trips for today include all alternatives and directions
  trips_number_today = data[['line_id', 'trip_id','trip_date', 'stop_sequence']]
  trips_number_today = trips_number_today[ trips_number_today['stop_sequence'] == 1] 
  values_to_render['trips_number_today'] = trips_number_today.shape[0]  # number of trips today.
  route_number_today = trips_number_today['line_id'].drop_duplicates()
  values_to_render['route_number_today'] = route_number_today.shape[0] # number of routes today.
  
  #  popular and unpopular lines for agency
  popularity = data[['line_id', 'trip_id','trip_date']]
  popularity = popularity[['line_id','trip_id','trip_date']].drop_duplicates()
  popularity = popularity.groupby(['line_id'],as_index=False).count()
  popularity = popularity.sort_values(by=['trip_id'] ,ascending=True)
  #popular
  popular_line_id = popularity['line_id'].iloc[-1]
  popular_number_of_trips = popularity['trip_id'].iloc[-1]
  values_to_render['popular_number_of_trips'] = popular_number_of_trips # number of trips to popular route
  popular_data = data[data['line_id'] == popular_line_id]
  popular_data = popular_data[ ['route_id','route_long_name','line_number']]
  popular_data_temp = popular_data.groupby(['route_id'],as_index=False).count()
  popular_data_temp = popular_data_temp.sort_values(by=['route_long_name'] ,ascending=True)
  popular_route_id = popular_data_temp['route_id'].iloc[-1]
  popular_data = popular_data[popular_data['route_id'] == popular_route_id ]
  popular_route_name = popular_data['route_long_name'].iloc[0].split('<->')
  values_to_render['popular_route_name'] = popular_route_name # add popular name route to dictionary
  values_to_render['popular_route_number'] = popular_data['line_number'].iloc[0]  # add popular number route to dictionary
  #unpopular
  unpopular_line_id = popularity['line_id'].iloc[0]
  unpopular_number_of_trips = popularity['trip_id'].iloc[0]
  values_to_render['unpopular_number_of_trips'] = unpopular_number_of_trips # number of trips to unpopular route
  unpopular_data = data[data['line_id'] == unpopular_line_id]
  unpopular_data = unpopular_data[ ['route_id','route_long_name','line_number']]
  unpopular_data_temp = unpopular_data.groupby(['route_id'],as_index=False).count()
  unpopular_data_temp = unpopular_data_temp.sort_values(by=['route_long_name'] ,ascending=True)
  unpopular_route_id = unpopular_data_temp['route_id'].iloc[-1]
  unpopular_data = unpopular_data[unpopular_data['route_id'] == unpopular_route_id ]
  unpopular_route_name = unpopular_data['route_long_name'].iloc[0].split('<->')
  values_to_render['unpopular_route_name'] = unpopular_route_name # add unpopular name route to dictionary
  values_to_render['unpopular_route_number'] = unpopular_data['line_number'].iloc[0]  # add unpopular number route to dictionary
  
  
  #
  today_schedule_times = data[['departure_time','stop_sequence']]
  today_schedule_times = today_schedule_times[ today_schedule_times['stop_sequence'] == 1 ]
  today_schedule_times = today_schedule_times['departure_time'].values.tolist()
  hours = ["04 - 06", "06 - 08", "08 - 10", "10 - 12" , "12 - 14",
   "14 - 16", "16 - 18" , "18 - 20" , "20 - 22", "22 - 24", "24 - 28"] # histogram hours ranges.

  title = 'Number of Trips Done by the Agency, Divided Into Hour Ranges' if lang=='en' else 'כמות הנסיעות שמבצע המפעיל, בחלוקה לטווחי שעות'
  y_title = 'Number of Trips' if lang=='en' else 'מספר נסיעות'
  x_title = 'Hour Range' if lang=='en' else 'טווחי שעות'
  
  # hours_histogram_picture = histogram_picture(hours,histogram_list_trip_per_hours(today_schedule_times),x_axis,y_axis,title) # histogram picture of route
  # values_to_render['hours_histogram_picture'] = hours_histogram_picture

  values_to_render['hours_histogram_interactive_graph'] = histogram_plotly(hours, histogram_list_trip_per_hours(today_schedule_times), x_title, y_title, title)
  
  """
    column_line_OTP, rows_line_OTP = line_OTP(report_date, line_id,direction)
  actual_trip_ids = tripids_for_line_OTP(report_date, line_id,direction) # a list of the trip_ids that actually happend

  ### ADDED ON 24.04.21 ###
  values_to_render['query_time_OTP'] = round(time.time()-time_initiate,3) # the time the query took in seconds
  ### ADDED ON 24.04.21 ###

  for i in range(len(today_schedule_times_and_tripids)):
    for j in range(len(today_schedule_times_and_tripids[i])):
      if str(today_schedule_times_and_tripids[i][j][1]) in actual_trip_ids:
        today_schedule_times_and_tripids[i][j][1] = "✅" # mark this trip as happend
      else:
        today_schedule_times_and_tripids[i][j][1] = "❌" # mark this trip as not happend

  values_to_render['today_departure_times'] = today_schedule_times_and_tripids

  column_line_OTP = [ x[0] for x in column_line_OTP ] # column name appear at index 0 at cursor.description
  data_line_OTP = pd.DataFrame( rows_line_OTP , columns=column_line_OTP ) # create DataFrame from column and SQL query table.
  if data_line_OTP['number_of_actual_trips'].iloc[0] is None:
    values_to_render['number_of_actual_trips'] = 0
  else:
    values_to_render['number_of_actual_trips'] = data_line_OTP['number_of_actual_trips'].iloc[0]
  values_to_render['number_of_missed_trips'] = number_trip_today - values_to_render['number_of_actual_trips']
  prec_of_actual_trips = int(100*values_to_render['number_of_actual_trips']/number_trip_today)
  prec_of_missed_trips = 100 - prec_of_actual_trips
  labels = 'Recorded Trips','Unrecorded Trips'
  sizes = [ prec_of_actual_trips , prec_of_missed_trips ]
  values_to_render['actual_and_missed_trips_picture'] = pie_chart(labels,sizes,3)
  """
  actual_trip_ids = data[['trip_id', 'trip_date', 'stop_sequence','departure_time', 'actual_time']]
  actual_trip_ids = actual_trip_ids[actual_trip_ids['stop_sequence']==1]
  number_trip_today = actual_trip_ids.shape[0]

  values_to_render['number_of_missed_trips'] = actual_trip_ids['actual_time'].apply(lambda x: True if x == '' else False).sum()          # .isnall.sum()     
  values_to_render['number_of_actual_trips'] = number_trip_today - values_to_render['number_of_missed_trips']
  prec_of_actual_trips = int(100*values_to_render['number_of_actual_trips']/number_trip_today) 
  prec_of_missed_trips = 100 - prec_of_actual_trips

  if lang=='en':
    title = 'Trips'
    group_title = 'Classification'
    number_title = 'Number of trips'
    labels = 'Recorded Trips','Unrecorded Trips'
  else:
    title = 'נסיעות'
    group_title = 'סיווג'
    number_title = 'מספר נסיעות'
    labels = 'נסיעות מתועדות', 'נסיעות לא מתועדות'

  sizes = [ prec_of_actual_trips , prec_of_missed_trips ]
  numbers = [values_to_render['number_of_actual_trips'], values_to_render['number_of_missed_trips']]
  # values_to_render['actual_and_missed_trips_picture'] = pie_chart(labels,sizes,3)
  values_to_render['actual_and_missed_trips_interactive_graph'] = pie_plotly(labels, numbers, group_title, number_title, title)
  
  return values_to_render
 
  
 ######################################################## End report agency ############################################################### 

# Function that create list of all cities depend on address of station in Database.
def list_of_cities():
  # query for get adress of all station.
  with connections['monitoring_warehouse'].cursor() as cursor:
    cursor.execute("SELECT stop_city FROM stops")
  rows = cursor.fetchall()
  cities = pd.DataFrame( rows , columns=['stop_city'] )
  cities = cities['stop_city'].drop_duplicates().values.tolist()
  
  """
  cities=[] # list of cities
  for line in rows:
    sys.stdout.write(line[0])
    city= line[0][line[0].find("עיר:")+5 : line[0].find("רציף:")-1] # separated city name from the address
    cities.append((city, city ))
  cities = list(dict.fromkeys(cities)) # prevent duplicate cities.
  cities=sorted(cities)
  """
  
  return cities


########### export to csv ###########
def export_to_csv(data,line_number,city,direction):
  response = HttpResponse(content_type='text/csv')
  data.to_csv(path_or_buf=response,encoding='utf-8-sig')
  response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.csv'%(line_number,city,direction)
  return response


## Function for trips divided by hours (bins)
def today_departure_times(today_schedule):
  # input: string list
  # output: list of string lists
  departure_times = [[] for i in range(11)] # capture departure_times against occurence
  time_differences = [[] for i in range(11)] # capture time difference between planned and actual time values
  bins = ["06:00:00", "08:00:00", "10:00:00", "12:00:00", "14:00:00", "16:00:00", "18:00:00", "20:00:00", "22:00:00", "24:00:00", "28:00:00"]
  for trip in today_schedule:                                     # for each trip in today's schedule
    for i in range(len(bins)):                                    # and for each bin in bins
      if trip[0]<bins[i]:                                         # if current trip is part of the current bin
        departure_times[i].append([str(trip[0][:5]),trip[1]])     # add its departure time to the relevant bin with the relevant trip id
        if trip[2] != 'nan':                                      # if the actual time is exists
          time_differences[i].append(trip[2])                     # add its time difference in relation to the planned departure time
        break
  
  time_differences_final = []
  for interval in time_differences:
    this_interval = []
    for time in interval:
      # include only valid actual time values
      if time != 'None':
        x = int(time)
        this_interval.append(x)
    
    if this_interval: # the interval indeed has actual time values
      time_differences_final.append("%.2f"%(int(np.mean(this_interval))/60)) # in minutes
    else:
      time_differences_final.append("--") # no info

  return departure_times, time_differences_final

def unknown_trips_check(report_date, today_schedule_times_and_tripids):
  all_trips_and_times = [trip for bin in today_schedule_times_and_tripids for trip in bin]
  interval_list = working_intervals(report_date)
  unknown_trip_ids = []

  if interval_list: # only if there are existing time intervals
    for trip in all_trips_and_times: # for each trip, check if it is outside intervals
      current_time = pd.to_timedelta(trip[0]+":00")
      intervals_check = [True for interval in interval_list if current_time<=interval[1] and current_time>=interval[0]]
      if not intervals_check: # if the departure time does not exist in one of the intervals, and it didn't happen
        unknown_trip_ids.append(trip[1])

  return unknown_trip_ids


# Function that create histogram list, count departure for each range.
def histogram_list_trip_per_hours(times):
  # input: list of strings (Hours range)
  # output: list of integers.
  histo=[0 for i in range(11)]
  # 04-06: 0, 06-08: 1, 08-10: 2, 10-12: 3, 12-14: 4, 14-16: 5, 16-18: 6, 18-20: 7, 20-22:8, 22-24:9, 24 until end of service: 10
  # Day trips are between the hours 04-28 where 24-28 is the early morning of the day afterwards
  bins = ["06:00:00", "08:00:00", "10:00:00", "12:00:00", "14:00:00", "16:00:00", "18:00:00", "20:00:00", "22:00:00", "24:00:00", "28:00:00"]
  for time in times:              # for each time in times list
    for i in range(len(bins)):    # for each bin from the bins list
      if time<bins[i]:            # if current time is lower than the bin,
        histo[i]+=1               # then add it to the bin
        break                     # and continue to the next time
  return histo
  
# Function that create histogram picture  
def histogram_picture(titles, values, xlabel, ylabel, graph_title, size=1): # for the trips hours histogram
    height = values
    #bars = tuple(titles)
    y_pos = titles 
    # Create bars and choose color
    bars = plt.bar(y_pos, height,  linewidth=1)
    # color = (0.5,0.1,0.5,0.6)
    # Add title and axis names
    plt.title(graph_title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    
    #plt.tick_params(axis='x', which='major', pad=7)  
    fig = plt.gcf() 
    #plt.gca().margins(x=0)
    plt.gcf().canvas.draw()
    
    # figure size
    if size==1: # Graph in bus line report
      fig.set_figheight(3.44)
      fig.set_figwidth(8)
    elif size==2: # Graph in station's report
      fig.set_figheight(3.44)
      fig.set_figwidth(8)
    elif size==3:
      fig.set_figheight(3.44)
      fig.set_figwidth(8)

    '''  
    tl = plt.gca().get_xticklabels()
    maxsize = max([t.get_window_extent().width for t in tl])
    m = 0.22 # inch margin
    s = maxsize/plt.gcf().dpi*len(height)+2*m
    margin = m/plt.gcf().get_size_inches()[0]
    
    plt.gcf().subplots_adjust(left=margin, right=1.-margin)
    plt.gcf().set_size_inches(s, plt.gcf().get_size_inches()[1])
    '''

    # print on each bar its value
    for bar in bars:
      yval = bar.get_height()
      plt.text(bar.get_x() + bar.get_width() / 2, yval , yval,
            ha='center', va='bottom')

    # set y axis height to be enough high for the values to show correctly
    max_num = max(values)
    add_by = max_num*1.2 if max_num>10 else max_num+1
    plt.ylim(0, int(add_by))


    buf= io.BytesIO()
    fig.savefig( buf, format='png', bbox_inches="tight")
    buf.seek(0)
    string = base64.b64encode( buf.read() )
    uri = urllib.parse.quote( string )
    plt.show()
    plt.close()
    return uri
    
def pie_chart(labels, sizes , size=1):
  #labels = 'Frogs', 'Hogs', 'Dogs', 'Logs'
  #sizes = [15, 30, 45, 10]
  #explode = (0, 0.1, 0, 0)  # only "explode" the 2nd slice (i.e. 'Hogs')
  fig, ax1 = plt.subplots()
  # ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',shadow=True, startangle=90)
  if len(labels)<2:
    ax1.pie(sizes, labels=labels, colors=['gray'], autopct='%1.1f%%',shadow=True, startangle=90)
  else:
    ax1.pie(sizes, labels=labels, colors=['green','red','gray'], autopct='%1.1f%%',shadow=True, startangle=90)
  ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
  
  #plt.tick_params(axis='x', which='major', pad=7)  
  fig = plt.gcf() 
  #plt.gca().margins(x=0)
  plt.gcf().canvas.draw()
  
  # figure size
  if size==1: # Graph in bus line report
    fig.set_figheight(4.2)
    fig.set_figwidth(8.78)
  elif size==2: # Graph in station's report
    fig.set_figheight(4.2)
    fig.set_figwidth(8.78)
  elif size==3:
    fig.set_figheight(4.2)
    fig.set_figwidth(8.78)
  
  buf= io.BytesIO()
  fig.savefig( buf, format='png', bbox_inches="tight")
  buf.seek(0)
  string = base64.b64encode( buf.read() )
  uri = urllib.parse.quote( string )
  
  plt.show()
  plt.close()
  return uri


def histogram_plotly(x, y, x_title, y_title, graph_title):
  """This function creates an interactive plotly graph"""
  df = pd.DataFrame({x_title: x, y_title: y})
  figure = px.bar(df, x=x_title, y=y_title, title=graph_title)
  figure = figure.update_layout(title_text=graph_title, title_x=0.5)
  return figure.to_html(full_html=False, default_height=350, default_width=700)

def pie_plotly(numbers, labels, group_title, number_title, graph_title):
  """This function creates an interactive plotly pie chart"""
  df = pd.DataFrame({group_title: labels, number_title: numbers})
  figure = px.pie(df, names=group_title, values=number_title, title=graph_title)
  figure = figure.update_layout(title_text=graph_title, title_x=0.5)
  return figure.to_html(full_html=False, default_height=450, default_width=900)


  
def min_and_max_difference_between_station(station_lst): # get list of stations distances and ruturn the min and max difference
  max_diff=0
  min_diff=station_lst[-1]
  for i in range(1, len(station_lst) ):
    if station_lst[i]-station_lst[i-1]<min_diff:
      min_diff=station_lst[i]-station_lst[i-1]
    if station_lst[i]-station_lst[i-1]>max_diff:
      max_diff=station_lst[i]-station_lst[i-1]
  #min_diff=describe_distance( min_diff )  we stop using this function due to HE/EN versions.
  #max_diff=describe_distance( max_diff )  we stop using this function due to HE/EN versions.
  return min_diff,max_diff
  
def describe_distance(distance): # get int distance and return string describe that distance by meter or KM
  # input: int                e.g. : 1500
  # output: string            e.g.: "1.5 KM"
  if distance>1000:
    distance= str( round(distance/1000,1))+" KM"
  else:
    distance= str( int(round(distance,0)) )+" Meter"
  return distance
 
# claculate trip time length 
def time_length( first_departure_time, last_departure_time):
  # input: string,string            e.g.: '20:00:00', '21:10:23'
  # outpou: string                  e.g.: '1 hour and 10 minutes'
  string="" 
  finish_time=1
  start_time=0
  start_time=str(first_departure_time)
  start_time=60*int(start_time[:2])+int(start_time[3:5]) # calculate start time 
  finish_time=str(last_departure_time)
  finish_time=60*int(finish_time[:2])+int(finish_time[3:5]) # calculate end time
  hour=0
  if finish_time-start_time>60: # calculate time trip by hours and minute
    hour= int(((finish_time-start_time)-(finish_time-start_time)%60)/60)
    minute = int( (finish_time-start_time)-60*hour)
  else:
    minute= int(finish_time-start_time)
    """
  if hour>0: # create representative string to user about how long the trip will be
    string=str(hour)+" hours and "+str(minute)+" minutes"
  else:
    string=str(minute)+" minutes"
    """
  return hour,minute

  
# string that describe frequency of schedule 
def frequency(times):
  # input: list of stirng (list of times)  e.g.: ['08:00:00', '09:00:00' , '10:00:00', '12:00:00']
  # output: string of time travel length.  e.g.: "1 hours and 20 minutes"
  string=" "
  hour=0
  start_time= 60*int(times[0][:2])+int(times[0][3:5])
  finish_time= 60*int(times[-1][:2])+int(times[-1][3:5])
  frequency= int( round((finish_time-start_time)/len(times)-1 , 0)) #
  if frequency>60:
    hour= int( ((frequency)-(frequency)%60) /60 )
    minute = int((frequency)-60*hour)
  elif frequency==-1:
    return "--"
  else:
    minute=frequency
    
  """
  if hour>0:
    string=str(hour)+" hours and "+str(minute)+" minutes"
  else:
    string=str(minute)+" minutes"
  """
  
  return hour,minute
 