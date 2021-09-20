# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models





class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'

class Agency(models.Model):
    agency_id = models.IntegerField(primary_key=True)
    agency_name = models.CharField(max_length=100)
    agency_url = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = 'agency'
        
        
class Routes(models.Model):
    route_id = models.IntegerField(primary_key=True)
    agency = models.ForeignKey(Agency, models.DO_NOTHING)
    line_number = models.IntegerField()
    route_long_name = models.CharField(max_length=200)
    line_id = models.IntegerField()
    direction = models.IntegerField()
    alternative = models.CharField(max_length=2)

    class Meta:
        managed = False
        db_table = 'routes'


class Stops(models.Model):
    stop_id = models.IntegerField(primary_key=True)
    stop_code = models.IntegerField()
    stop_name = models.CharField(max_length=200)
    stop_desc = models.CharField(max_length=200)
    stop_lat = models.FloatField()
    stop_lon = models.FloatField()
    location_type = models.IntegerField()
    parent_station = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stops'


class Trips(models.Model):
    trip_id = models.IntegerField(primary_key=True)
    trip_date = models.DateField()
    trip_headsign = models.CharField(max_length=100)
    route = models.ForeignKey(Routes, models.DO_NOTHING)
    direction_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'trips'
        unique_together = (('trip_id', 'trip_date'),)



class StopTimes(models.Model):
    trip = models.OneToOneField('Trips', models.DO_NOTHING, primary_key=True)
    trip_date = models.ForeignKey('Trips', models.DO_NOTHING, db_column='trip_date', related_name = 'stop_times_trip_date')
    stop_sequence = models.IntegerField()
    stop = models.ForeignKey('Stops', models.DO_NOTHING)
    departure_time = models.CharField(max_length=8)
    shape_dist_traveled = models.IntegerField()
    actual_time = models.CharField(max_length=8, blank=True, null=True)
    accuracy = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stop_times'
        unique_together = (('trip', 'trip_date', 'stop_sequence'),)



