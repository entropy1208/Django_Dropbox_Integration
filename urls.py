# -*- coding: utf-8 -*-
from __future__ import absolute_import


from django.conf.urls import url


from . import views


urlpatterns = [
    url(r'^index/$', views.index, name='index'),
    url(r'^upload/(?P<path>.*)$', views.upload, name='upload'),
    url(r'^action/(?P<action_name>[\w]+)/(?P<path>.*)$', views.action, name='action'),
    url(r'^search/$', views.search, name='search'),
    url(r'^dropbox_login/$', views.dropbox_login, name='dropbox_login'),
    url(r'^dropbox-auth-start/$', views.dropbox_auth_start, name='dropbox_auth_start'),
]
