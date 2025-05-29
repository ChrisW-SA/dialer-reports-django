from django.urls import path 

from dialer_reports import views 



urlpatterns = [
    path('dashboard/', views.dashboard, name='dialer-reports-dashboard'),
    path('campaigns/', views.campaigns, name='dialer-reports-campaigns'),
    path('campaign-details/<int:pk>', views.campaign_details, name='dialer-reports-campaign-details'),
    path('campaign-record-call-flow/<int:pk>', views.campaign_record_call_flow, name='dialer-reports-campaign-record-call-flow'),
    path('delete-campaign-confirmation/<int:pk>', views.delete_campaign_confirmation, name='dialer-reports-delete-campaign-confirmation'),
    path('delete-campaign/<int:pk>', views.delete_campaign, name='dialer-reports-delete-campaign'),
]
