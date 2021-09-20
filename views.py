# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io
import urllib, base64
from django.shortcuts import render
from django.shortcuts import redirect
from django.http import HttpResponse
from django.http import JsonResponse
from django import forms
from django.db import connections
from datetime import datetime, date, time, timedelta
from gtfs.pages import *
from gtfs.queries import *
from monitoring_warehouse.forms import BusLineForm, BusStationForm
from monitoring_warehouse.models import Agency, Stops, Routes, StopTimes
#from dal import autocomplete

# Create your views here.

## Update flag ##

def is_in_update():
  url = '/home/tal/PT/gtfs/update.txt'
  with open(url, 'r') as f:
    return f.read()

# Class for form in main_page.html 
class HomeForm(forms.Form):
  Choice=(('1','Stations of specific line bus'), ('2','Most 5 popular line buses for each bus company'),('3','Line buses at station'))
  report=forms.ChoiceField(label='Report', choices=Choice, initial='1', widget=forms.RadioSelect)
'''
# Class for form of line bus, conected to "Stations of specific line bus" report
class StationForm(forms.Form):
  cities=list_of_cities()
  line_number = forms.IntegerField(label='Line Number', min_value=1, max_value=1000)
  city = forms.CharField(label='City', widget=forms.Select(choices=cities))
  Choice=(('1','Direction 1'), ('2','Direction 2'))
  direction=forms.ChoiceField(label='Direction', choices=Choice, initial='1', widget=forms.RadioSelect)

# Class for form of bus station, conected to "Line buses at station" report    
class Bus_station(forms.Form):
  stations = list_of_station()
  station =  forms.CharField(label='Station', widget=forms.Select(choices=stations)) 
  '''
class AgencyForm(forms.Form):
  agencies_list = list_of_agencies()
  agencies = forms.ChoiceField(label='Agency', choices=agencies_list, widget=forms.RadioSelect)

# Function to render home page.
def home(request): 
  data=request.GET.dict()
  #form=HomeForm()
  #return render(request, 'index.html',{'form':form,'in_update': is_in_update()})
  # Allowing the option to change the website's language between English and Hebrew
  if data.get('lang'):
    path = 'he/' if data.get('lang') == 'he' else ''
  else:
    path = ''

  return render(request, path+'index.html',{'in_update': is_in_update()})

# Function to render about page.    
def about(request):
  data=request.GET.dict()
  # Allowing the option to change the website's language between English and Hebrew
  if data.get('lang'):
    path = 'he/' if data.get('lang') == 'he' else ''
  else:
    path = ''

  return render(request, path+'about.html', {'in_update': is_in_update()})

# Function to render line form.  
def line_form(request): 
  error = ''
  data=request.GET.dict()
  form = BusLineForm()
  max_date, min_date = max_date_for_forms(), min_date_for_forms()
  data_df = pd.read_csv("/var/www/mysite/monitoring_warehouse/cities_and_lines.csv")
  data_df = data_df.drop(columns=['Unnamed: 0'])
  cities = data_df.stop_city.drop_duplicates().to_list()

  # Allowing the option to change the website's language between English and Hebrew
  if data.get('lang'):
    path = 'he/' if data.get('lang') == 'he' else ''
  else:
    path = ''

  if request.GET.get('error') == '1': # in case there was no information returned
    if path=='':
      error = "There is no information for the chosen date."
    else:
      error = "אין מידע זמין עבור התאריך שנבחר."

    # Allowing the option to change the website's language between English and Hebrew
  if data.get('lang'):
    path = 'he/' if data.get('lang') == 'he' else ''
  else:
    path = ''
  
  return render(request, path+'form_line.html', {'form':form, 'error':error, 'current_date':max_date, 'min_date':min_date ,'in_update': is_in_update(), 'cities':cities})

############################ Start Dependent Autocomplete ####################################################
# AJAX - START
def load_lines(request):
  data_df = pd.read_csv("/var/www/mysite/monitoring_warehouse/cities_and_lines.csv")
  data_df = data_df.drop(columns=['Unnamed: 0'])
  stop_city = request.GET.get('stop_city')
  lines = data_df[data_df.stop_city == stop_city].drop_duplicates()
  lines = lines[['line_number','line_id']].values.tolist()
  return render(request, 'lines_dropdown_list_options.html', {'lines': lines})


def load_directions(request):
  data_df = pd.read_csv("/var/www/mysite/monitoring_warehouse/cities_and_lines.csv")
  data_df = data_df.drop(columns=['Unnamed: 0'])
  line_id = request.GET.get('line_id')
  stop_city = request.GET.get('stop_city')
  directions = data_df[(data_df.line_id == int(line_id)) & (data_df.stop_city.str.contains(str(stop_city)))]
  directions = directions.drop(['stop_city','line_number','line_id'], axis = 'columns')
  directions = directions.drop_duplicates().direction.str.split(pat = ",").to_list()[0]
  return render(request, 'directions_dropdown_list_options.html', {'directions': directions})


def load_stops(request):
  data_df = pd.read_csv("/var/www/mysite/monitoring_warehouse/all_stops.csv")
  data_df = data_df.drop(columns=['Unnamed: 0'])
  stop_city = request.GET.get('stop_city')
  data_df = data_df[data_df.stop_city == stop_city].drop_duplicates()
  data_df.drop('stop_city',axis='columns',inplace = True)
  stop_desc = sorted(data_df.values.tolist(), key=lambda x: x[0].split(' - ')[0])
  print(stop_desc)
  return render(request, 'stops_dropdown_list_options.html', {'stop_desc': stop_desc})

# AJAX - END
############################ End Dependent Autocomplete #####################################################


# Function to render agency form.  
def agency_form(request):
  error = ''
  data=request.GET.dict()
  form = AgencyForm()
  max_date,min_date = max_date_for_forms(), min_date_for_forms()
  #current_day_name = date.today().strftime("%A")
  agencies = list_of_agencies()

  # Allowing the option to change the website's language between English and Hebrew
  if data.get('lang'):
    path = 'he/' if data.get('lang') == 'he' else ''
  else:
    path = ''

  if request.GET.get('error') == '1': # in case there was no information returned
    if path=='':
      error = "There is no information for the chosen date."
    else:
      error = "אין מידע זמין עבור התאריך שנבחר."

  return render(request, path+'form_agency.html', {'form':form, 'agencies': agencies, 'current_date':max_date, 'min_date':min_date, 'error': error ,'in_update': is_in_update()})

# Function to render station form.     
def station_form(request):
  error=''
  data=request.GET.dict()

  form = BusStationForm()
  data_df = pd.read_csv("/var/www/mysite/monitoring_warehouse/all_stops.csv")
  data_df = data_df.drop(columns=['Unnamed: 0'])
  cities = data_df.sort_values(by=['stop_city']).stop_city.drop_duplicates().to_list()
  max_date,min_date = max_date_for_forms(), min_date_for_forms()
  
  # Allowing the option to change the website's language between English and Hebrew
  if data.get('lang'):
    path = 'he/' if data.get('lang') == 'he' else ''
  else:
    path = ''

  if request.GET.get('error') == '1': # in case there was no information returned
    if path=='':
      error = "There is no information for the chosen date."
    else:
      error = "אין מידע זמין עבור התאריך שנבחר."

  return render(request, path+'form_station.html', {'form':form, 'cities':cities , 'current_date':max_date, 'min_date':min_date, 'error': error , 'in_update': is_in_update()})

# Function to render the form by user choice  . 
def choose_report(request):
	data=request.GET.dict()
	if not data: # in case we haven't received the right option
		return redirect('/')
	
	
	if data.get('report')=='1': 
		form=StationForm()
		return render(request, 'form_line.html', {'form':form,'in_update': is_in_update(), 'cities_list': cities_list})
      
	elif data.get('report')=='2':
		#trip number as of today!!
		form = AgencyForm()
		current_date = str(date.today())
		current_day = date.today().strftime("%A")
		agencies = list_of_agencies()
		return render(request, 'form_agency.html', {'form':form, 'agencies': agencies})
		
	#row = most_popular_routes(current_date) # function with query to calculate top 5 popular route of agencies 3, 5 and 15.
	#agencies=[x[0] for x in row] # get the agency names from first column
	#agencies = list(dict.fromkeys(agencies)) # remove duplicate of agency names
	#return render(request, 'most_popular.html', {'agencies':agencies, 'current_date': current_date, 'current_day': current_day, 'query':row, 'in_update': is_in_update()}) 
        
	elif data.get('report')=='3':
		form=Bus_station()
		stations = list_of_station()
		return render(request, 'form_station.html', {'form':form, 'stations': stations,'in_update': is_in_update()})
      
	else:
		return redirect('/')     
        
############################ Start Line Report #####################################################
      
 # Function to render the result of "Stations of specific line bus" form.   
def line_report(request):
  error = ''
  data = request.GET.dict()
  if not data: # in case there is no received GET data
    return redirect('/line_form/')

  # Allowing the option to change the website's language between English and Hebrew
  if data.get('lang'):
    path = 'he/' if data.get('lang') == 'he' else ''
    lang = 'he' if data.get('lang') == 'he' else 'en'
  else:
    path,lang = '','en'

  
  line_id = data.get('line_id')
  line_id= int(line_id)
  city = data.get('origin_city')
  direction=data.get('direction')
  direction= int(direction)
  report_date = data.get('report_date')
  direction_flag = data.get('direction_flag')
  report_date= "'"+report_date+"'"

  #agency_name, route_name, estimated_travel_time, estimated_avarage_speed, length_travel, average_distance_between_stops, min_distance , max_distance ,number_trip_today, first_trip, last_trip , today_frequency ,today_popularity_among_his_agency, trip_city , picture, list_trip_stations 
  values_to_render = reports_for_line(line_id, city, direction, report_date, lang)

  export=data.get('export')
  if export: # export to csv
    response = HttpResponse(content_type='text/csv')
    str_response = 'attachment; filename=line_{}_report_{}.csv'.format(str(values_to_render['line_number']), str(report_date[1:-1]))
    response['Content-Disposition'] = str_response
    response.write(u'\ufeff'.encode('utf8'))
    values_to_render['data'].to_csv(path_or_buf=response,encoding='utf-8-sig', index=False)
    return response
    
    
  # in case values_to_render is empty, redirect to a relevant page
  if not values_to_render:
    if lang=='en':
      return redirect('/line_form/?error=1')
    else:
      return redirect('/line_form/?error=1&lang=he')
    
  values_to_render['origin_city'] = city
  values_to_render['direction_flag'] = direction_flag
  if direction=='1':
      directionstr = 'Direction 1'
  else:
      directionstr = 'Direction 2'
  values_to_render['directionstr'] = directionstr
  values_to_render['report_date'] = report_date[1:-1]
  values_to_render['in_update'] = is_in_update()  
  values_to_render['line_id'] = line_id 
  #return render(request, 'report_line.html', values_to_render )

  values_to_render['max_date'], values_to_render['min_date'] = max_date_for_forms() ,min_date_for_forms()

  return render(request, path+'bus_line_page.html', values_to_render )

############################ End Line Report #####################################################

############################ Start Agency Report ##################################################### 

# Function to render agency report.      
def agency_report(request):
  error = ''
  data = request.GET.dict()
  if not data: # in case there is no received GET data
    return redirect('/agency_form/')


  # Allowing the option to change the website's language between English and Hebrew
  if data.get('lang'):
    path = 'he/' if data.get('lang') == 'he' else ''
    lang = 'he' if data.get('lang') == 'he' else 'en'
  else:
    path,lang = '','en'

  agency = data.get('agency')
  report_date = data.get('report_date')
  values_to_render = reports_for_agency(agency ,report_date, lang)

  export=data.get('export')
  if export: # export to csv
    response = HttpResponse(content_type='text/csv')
    str_response = 'attachment; filename=agency_{}_report_{}.csv'.format(agency, report_date)
    response['Content-Disposition'] = str_response
    response.write(u'\ufeff'.encode('utf8'))
    values_to_render['data'].to_csv(path_or_buf=response,encoding='utf-8-sig', index=False)
    return response

  # in case values_to_render is empty, redirect to a relevant page
  if not values_to_render:
    if lang=='en':
      return redirect('/agency_form/?error=1')
    else:
      return redirect('/agency_form/?error=1&lang=he')

  values_to_render['report_date'] = report_date
  values_to_render['in_update'] = is_in_update()

  values_to_render['max_date'], values_to_render['min_date'] = max_date_for_forms() ,min_date_for_forms()

  return render(request, path+'agency_page.html', values_to_render )
  
############################ End Agency Report ####################################################### 
    
 
 
############################ Start Station Report ####################################################   
    
 # Function to render the result of "Line buses at station" form.       
def bus_station_report(request):
  data = request.GET.dict()
  if not data: # in case there is no received GET data
    if lang=='en':
      return redirect('/station_form/')
    else:
      return redirect('/station_form/?lang=he')

  # Allowing the option to change the website's language between English and Hebrew
  if data.get('lang'):
    path = 'he/' if data.get('lang') == 'he' else ''
    lang = 'he' if data.get('lang') == 'he' else 'en'
  else:
    path,lang = '','en'

  station = data.get('station')
  report_date = data.get('report_date')
  values_to_render = reports_for_station( station , report_date, lang)
  # in case values_to_render is empty, redirect to a relevant page
  if not values_to_render:
    if lang=='en':
      return redirect('/station_form/?error=1')
    else:
      return redirect('/station_form/?error=1&lang=he')
  
  export=data.get('export')
  if export: # export to csv
    response = HttpResponse(content_type='text/csv')
    str_response = 'attachment; filename=station_{}_report_{}.csv'.format(values_to_render['stop_code'], report_date)
    response['Content-Disposition'] = str_response
    response.write(u'\ufeff'.encode('utf8'))
    values_to_render['data'].to_csv(path_or_buf=response,encoding='utf-8-sig',index=False)
    return response

  values_to_render['stop_id'] = station
  values_to_render['in_update'] = is_in_update()
  values_to_render['report_date'] = report_date

  values_to_render['max_date'], values_to_render['min_date'] = max_date_for_forms() ,min_date_for_forms()

  return render(request, path+'bus_station_page.html', values_to_render )
    
############################ End Station Report ######################################################     







