"""
Analytics URLs.
"""
from django .urls import path ,include 
from rest_framework .routers import DefaultRouter 

from apps .analytics .views import (
DashboardAnalyticsView ,UserActivityViewSet ,SystemMetricViewSet ,
)

# Comment_74
analytics_view_overview =DashboardAnalyticsView .as_view ({'get':'overview'})
analytics_view_security =DashboardAnalyticsView .as_view ({'get':'security'})
analytics_view_activity_feed =DashboardAnalyticsView .as_view ({'get':'activity_feed'})

router =DefaultRouter ()
router .register (r'activities',UserActivityViewSet ,basename ='activity')
router .register (r'metrics',SystemMetricViewSet ,basename ='metric')

urlpatterns =[
path ('dashboard/overview/',analytics_view_overview ,name ='dashboard-overview'),
path ('dashboard/security/',analytics_view_security ,name ='dashboard-security'),
path ('dashboard/activity-feed/',analytics_view_activity_feed ,name ='dashboard-activity-feed'),
path ('dashboard/activity_feed/',analytics_view_activity_feed ,name ='dashboard-activity-feed-underscore'),
path ('',include (router .urls )),
]
