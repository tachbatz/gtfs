from django.urls import path
from gtfs import views
from django.conf.urls import *
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns




urlpatterns = [
	path('', views.home, name="home"),
	path('about/',views.about, name="about"),
	path('create/', views.choose_report, name = 'choose_report' ),
	path('lines_report/', views.line_report, name = 'line_report' ), 
	path('bus_station_report/', views.bus_station_report, name='bus_station_report'),
	path('agency_report/', views.agency_report, name='agency_report'),
  	path('line_form/', views.line_form, name='line_form'),
  	path('agency_form/', views.agency_form, name='agency_form'),
  	path('station_form/', views.station_form, name='station_form'),
	  
	path('ajax/load-lines/', views.load_lines, name='ajax_load_lines'), # AJAX
	path('ajax/load-directions/', views.load_directions, name='ajax_load_directions'), # AJAX
	path('ajax/load-stops/', views.load_stops, name='ajax_load_stops'), # AJAX
]