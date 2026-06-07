from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import LoginLog
import requests

@receiver(user_logged_in)
def track_login(sender, request, user, **kwargs):
    if hasattr(request, '_qr_logged'):
        return

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    lat, lon = None, None
    
    # Geolocalización (Solo si no es localhost para el efecto WOW)
    try:
        if ip != '127.0.0.1':
            response = requests.get(f'http://ip-api.com/json/{ip}').json()
            if response.get('status') == 'success':
                lat = response.get('lat')
                lon = response.get('lon')
        else:
            # Simulamos una posición en Madrid para el modo local
            lat, lon = 40.4168, -3.7038
    except:
        pass

    LoginLog.objects.create(
        user=user,
        login_type='NORMAL',
        ip_address=ip,
        user_agent=request.META.get('HTTP_USER_AGENT'),
        latitude=lat,
        longitude=lon
    )
