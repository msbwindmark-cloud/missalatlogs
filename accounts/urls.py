from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    # Use built-in Django login for the normal flow, but directed to our custom template
    path('login/normal/', auth_views.LoginView.as_view(template_name='accounts/login_normal.html'), name='login_normal'),
    path('login-qr/', views.qr_login_view, name='qr_login'),
    path('api/qr-scan/', views.qr_scan_api, name='qr_scan_api'),
    path('api/log-intruder/', views.log_intruder, name='log_intruder'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('api/dashboard-data/', views.get_dashboard_data, name='get_dashboard_data'),
    path('export/excel/', views.export_logs_excel, name='export_logs_excel'),
    path('export/pdf/', views.export_intruders_pdf, name='export_intruders_pdf'),
    path('request-new-qr/', views.request_new_qr, name='request_new_qr'),
    path('', views.dashboard, name='home'),
    path('solicitar-qr-login/', views.request_qr_from_login, name='request_qr_from_login'),
    # Añade esto al final de tus urlpatterns existentes:
    path('api/log-salat-query/', views.log_salat_query, name='log_salat_query'),
]
