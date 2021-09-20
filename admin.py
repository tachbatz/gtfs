from django.contrib import admin
from gtfs.models import Agency
from gtfs.models import Routes
from gtfs.models import Stops
from gtfs.models import Trips
from gtfs.models import StopTimes

# Register your models here.
admin.site.register(Agency)
admin.site.register(Routes)
admin.site.register(Stops)
admin.site.register(Trips)
admin.site.register(StopTimes)