from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm
from .models import QRToken, LoginLog, AccessAttempt, SalatQueryLog
import qrcode
import io
import base64
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count

from django.core.mail import send_mail, EmailMultiAlternatives, EmailMessage
from email.mime.image import MIMEImage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.models import User

import json
from django.views.decorators.csrf import csrf_exempt



def log_user_login(request, user, login_type):
    import requests
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    lat, lon = None, None
    try:
        if ip != '127.0.0.1':
            response = requests.get(f'http://ip-api.com/json/{ip}').json()
            if response.get('status') == 'success':
                lat, lon = response.get('lat'), response.get('lon')
        else:
            lat, lon = 40.4168, -3.7038
    except:
        pass
    
    LoginLog.objects.create(
        user=user,
        login_type=login_type,
        ip_address=ip,
        user_agent=request.META.get('HTTP_USER_AGENT'),
        latitude=lat,
        longitude=lon
    )


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            user_email = form.cleaned_data.get('email')
            
            # Generate QR Token
            token_obj = QRToken.objects.create(user=user)
            
            # Generate QR URL
            qr_url = request.build_absolute_uri(reverse('qr_login')) + f"?token={token_obj.token}"
            
            # 1. Generar la imagen QR en memoria
            img = qrcode.make(qr_url)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            qr_bytes = buf.getvalue()
            
            # Preparar base64 para la vista de éxito en la web
            qr_base64 = base64.b64encode(qr_bytes).decode()

            # 2. Configurar el correo electrónico (Texto plano y HTML)
            subject = 'Tu Código QR de Acceso Seguro - QRLogin'
            
            # Cuerpo en texto plano (por si el gestor no soporta HTML)
            text_content = f'Hola {username},\n\nGracias por registrarte. Usa este enlace para entrar:\n\n{qr_url}'
            
            # Cuerpo en HTML con la imagen incrustada usando 'cid:qr_image'
            html_content = f"""
            <html>
                <body>
                    <p>Hola <strong>{username}</strong>,</p>
                    <p>Gracias por registrarte. Puedes escanear el siguiente código QR para entrar o hacer clic en el enlace:</p>
                    <p><img src="cid:qr_image" alt="Código QR de Acceso" style="border:1px solid #ccc;" /></p>
                    <p><a href="{qr_url}">Hacer clic aquí para acceder directamente</a></p>
                </body>
            </html>
            """
            
            # Crear el objeto de correo
            email = EmailMultiAlternatives(
                subject, 
                text_content, 
                'no-reply@tuapp.com', 
                [user_email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # 3. Adjuntar la imagen QR de forma incrustada
            msg_img = MIMEImage(qr_bytes)
            msg_img.add_header('Content-ID', '<qr_image>')  # Este ID debe coincidir con el 'cid:' del HTML
            msg_img.add_header('Content-Disposition', 'inline', filename='qr_code.png')
            email.attach(msg_img)
            
            # Enviar correo
            email.send()
            
            # Auto login after register? No, let's make them use the QR or login normally
            messages.success(request, f'¡Cuenta creada! Se ha enviado un QR a {user_email}.')
            
            return render(request, 'accounts/register_success.html', {
                'username': username,
                'qr_base64': qr_base64,
                'qr_url': qr_url
            })
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})



def register_old(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            user_email = form.cleaned_data.get('email')
            
            # Generate QR Token
            token_obj = QRToken.objects.create(user=user)
            
            # Generate QR URL
            qr_url = request.build_absolute_uri(reverse('qr_login')) + f"?token={token_obj.token}"
            
            # Email (Mock)
            subject = 'Tu Código QR de Acceso Seguro - QRLogin'
            message = f'Hola {username},\n\nGracias por registrarte. Usa este enlace para entrar:\n\n{qr_url}'
            send_mail(subject, message, 'no-reply@tuapp.com', [user_email])
            
            # Auto login after register? No, let's make them use the QR or login normally
            messages.success(request, f'¡Cuenta creada! Se ha enviado un QR a {user_email}.')
            
            # Preparation for display just in case
            img = qrcode.make(qr_url)
            buf = io.BytesIO()
            img.save(buf)
            qr_base64 = base64.b64encode(buf.getvalue()).decode()

            return render(request, 'accounts/register_success.html', {
                'username': username,
                'qr_base64': qr_base64,
                'qr_url': qr_url
            })
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Check if it's a normal login post (if we used standard LoginView we'd hook into it)
    # But since we have a dedicated login_normal view, we handle logs over there or here.
    return render(request, 'accounts/login.html')

def qr_login_view(request):
    token_str = request.GET.get('token')
    if not token_str:
        return redirect('login')
    
    try:
        token_obj = QRToken.objects.get(token=token_str)
        if token_obj.is_valid():
            user = token_obj.user
            request._qr_logged = True # Evita duplicado en signals
            login(request, user)
            token_obj.is_used = True
            token_obj.save()
            
            log_user_login(request, user, 'QR')
            
            messages.success(request, f'Bienvenido {user.username}.')
            return redirect('dashboard')
    except QRToken.DoesNotExist:
        pass
    
    messages.error(request, 'Token inválido o expirado.')
    return redirect('login')



@login_required
def dashboard(request):
    # 1. Obtener la IP actual del usuario que solicita el dashboard
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_actual = x_forwarded_for.split(',')[0]
    else:
        ip_actual = request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    # Si estás en local (localhost), le damos un formato más bonito
    if ip_actual == '127.0.0.1':
        ip_actual = "127.0.0.1 (Localhost)"

    if request.user.is_superuser:
        # Primero obtenemos el último log global de forma limpia y directa sin límites
        ultimo_log = LoginLog.objects.order_by('-timestamp').first()
        
        # Ahora generamos las variables recortadas para pintar en las tablas del HTML
        logs = LoginLog.objects.all()[:20]
        qr_history = QRToken.objects.all()[:10]
        login_stats = LoginLog.objects.values('login_type').annotate(count=Count('id'))
        
        from .models import AccessAttempt
        intruder_attempts = AccessAttempt.objects.all()[:6]
    else:
        # Para usuarios normales, obtenemos primero el último log de forma directa de la base de datos
        ultimo_log = request.user.login_logs.order_by('-timestamp').first()
        
        # Luego generamos los sets recortados con el slice [:10] para no saturar la interfaz
        logs = request.user.login_logs.all()[:10]
        qr_history = request.user.tokens.all()[:5]
        login_stats = request.user.login_logs.values('login_type').annotate(count=Count('id'))
        intruder_attempts = []

    # Extraemos la hora de la última conexión de forma segura
    ultimo_login_hora = ultimo_log.timestamp.strftime("%H:%M") if ultimo_log else "--:--"

    return render(request, 'accounts/dashboard.html', {
        'logs': logs,
        'qr_history': qr_history,
        'login_stats': login_stats,
        'intruder_attempts': intruder_attempts,
        'ip_actual': ip_actual,
        'ultimo_login_hora': ultimo_login_hora
    })






@login_required
def dashboard_old2(request):
    # 1. Obtener la IP actual del usuario que solicita el dashboard
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_actual = x_forwarded_for.split(',')[0]
    else:
        ip_actual = request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    # Si estás en local (localhost), le damos un formato más bonito para que no se vea vacío
    if ip_actual == '127.0.0.1':
        ip_actual = "127.0.0.1 (Localhost)"

    if request.user.is_superuser:
        logs = LoginLog.objects.all()[:20]
        qr_history = QRToken.objects.all()[:10]
        login_stats = LoginLog.objects.values('login_type').annotate(count=Count('id'))
        
        from .models import AccessAttempt
        intruder_attempts = AccessAttempt.objects.all()[:6]
        
        # El superusuario ve el último login global del sistema
        ultimo_log = LoginLog.objects.first()
    else:
        # IMPORTANTE: Asegúrate de usar el mismo filtro/relación que usas abajo
        # Si en tu modelo usaste related_name='login_logs', esto es correcto:
        logs = request.user.login_logs.all()[:10]
        qr_history = request.user.tokens.all()[:5]
        login_stats = request.user.login_logs.values('login_type').annotate(count=Count('id'))
        intruder_attempts = []
        
        # Obtenemos el último inicio de sesión de este usuario específico
        ultimo_log = logs.first() if logs.exists() else None

    # Extraemos la hora de la última conexión de forma segura
    ultimo_login_hora = ultimo_log.timestamp.strftime("%H:%M") if ultimo_log else "--:--"

    return render(request, 'accounts/dashboard.html', {
        'logs': logs,
        'qr_history': qr_history,
        'login_stats': login_stats,
        'intruder_attempts': intruder_attempts,
        'ip_actual': ip_actual,             # <<-- Nueva variable explícita
        'ultimo_login_hora': ultimo_login_hora # <<-- Nueva variable explícita
    })




@login_required
def dashboard_old(request):
    if request.user.is_superuser:
        # Los superadmins ven todo lo que pasa en la plataforma
        logs = LoginLog.objects.all()[:20]
        qr_history = QRToken.objects.all()[:10]
        login_stats = LoginLog.objects.values('login_type').annotate(count=Count('id'))
        
        from .models import AccessAttempt
        intruder_attempts = AccessAttempt.objects.all()[:6]
    else:
        # Usuarios normales solo ven lo suyo
        logs = request.user.login_logs.all()[:10]
        qr_history = request.user.tokens.all()[:5]
        login_stats = request.user.login_logs.values('login_type').annotate(count=Count('id'))
        intruder_attempts = []
    
    return render(request, 'accounts/dashboard.html', {
        'logs': logs,
        'qr_history': qr_history,
        'login_stats': login_stats,
        'intruder_attempts': intruder_attempts
    })
@login_required
def get_dashboard_data(request):
    if request.user.is_superuser:
        locations = LoginLog.objects.exclude(latitude__isnull=True).values('latitude', 'longitude', 'timestamp', 'user__username', 'login_type')
        stats_query = LoginLog.objects.values('login_type').annotate(count=Count('id'))
    else:
        locations = request.user.login_logs.exclude(latitude__isnull=True).values('latitude', 'longitude', 'timestamp', 'user__username', 'login_type')
        stats_query = request.user.login_logs.values('login_type').annotate(count=Count('id'))
    
    # Formatear stats para JS
    stats = {item['login_type']: item['count'] for item in stats_query}
    
    return JsonResponse({
        'locations': list(locations),
        'stats': stats
    })

from django.views.decorators.csrf import csrf_exempt
import base64
from django.core.files.base import ContentFile

@csrf_exempt
def log_intruder(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        image_data = data.get('image')
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        
        from .models import AccessAttempt
        attempt = AccessAttempt.objects.create(
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT'),
            was_successful=False
        )

        if image_data:
            try:
                format, imgstr = image_data.split(';base64,')
                ext = format.split('/')[-1]
                img_data = ContentFile(base64.b64decode(imgstr), name=f'intruder_{attempt.id}.{ext}')
                attempt.photo.save(f'intruder_{attempt.id}.{ext}', img_data, save=True)
            except Exception as e:
                print(f"Error saving intruder photo: {e}")

        return JsonResponse({'status': 'logged'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def qr_scan_api(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        token_str = data.get('token', '')
        if 'token=' in token_str:
            token_str = token_str.split('token=')[-1]

        try:
            token_obj = QRToken.objects.get(token=token_str)
            if token_obj.is_valid():
                user = token_obj.user
                request._qr_logged = True
                login(request, user)
                token_obj.is_used = True
                token_obj.save()
                
                log_user_login(request, user, 'QR')
                
                return JsonResponse({'status': 'success'})
        except QRToken.DoesNotExist:
            pass
    return JsonResponse({'status': 'error', 'message': 'Token inválido'})


@login_required
def request_new_qr(request):
    user = request.user
    token_obj = QRToken.objects.create(user=user)

    # 1. Construir la URL absoluta
    qr_url = request.build_absolute_uri(reverse("qr_login"))
    full_url = f"{qr_url}?token={token_obj.token}"

    # 2. Generar la imagen del código QR en memoria
    qr = qrcode.QRCode(
        version=1,
        # Cambiamos a nivel HIGH (H) para que tenga más densidad de puntos y mejor lectura
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        # Subimos de 10 a 25 para duplicar con creces el tamaño en píxeles
        box_size=25,
        border=4,
    )
    qr.add_data(full_url)
    qr.make(fit=True)

    # Crear la imagen con Pillow
    img = qr.make_image(fill_color="black", back_color="white")

    # Guardar la imagen en un buffer de bytes en memoria
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # 3. Configurar el correo electrónico con el adjunto
    subject = "Tu Nuevo Código QR de Acceso Premium"
    message_body = (
        f"Hola {user.username},\n\n"
        f"Hemos generado un nuevo acceso seguro para ti.\n\n"
        f"Puedes iniciar sesión haciendo clic en el siguiente enlace:\n{full_url}\n\n"
        f"O bien, puedes escanear la imagen del código QR que adjuntamos en este correo.\n\n"
        f"Un saludo,\nEl equipo de QRLogin"
    )

    # Usamos EmailMessage para tener control total de los adjuntos
    email = EmailMessage(
        subject=subject,
        body=message_body,
        from_email="no-reply@tuapp.com",
        to=[user.email],
    )

    # Adjuntar el archivo indicando: (Nombre_Archivo, Contenido_Bytes, Tipo_Mime)
    email.attach(f"QR_Acceso_{user.username}.png", buffer.read(), "image/png")

    # 4. Enviar el correo
    try:
        email.send()
        messages.success(
            request, "Se ha enviado un nuevo código QR con su imagen a tu correo."
        )
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        messages.error(
            request,
            "El token se generó, pero hubo un problema al enviar el correo.",
        )
    
    return redirect("dashboard")



@login_required
def request_new_qr_old(request):
    user = request.user
    token_obj = QRToken.objects.create(user=user)
    qr_url = request.build_absolute_uri(reverse('qr_login')) + f"?token={token_obj.token}"
    
    # Email
    subject = 'Tu Nuevo Código QR de Acceso'
    message = f'Hola {user.username}, aquí tienes tu nuevo acceso:\n\n{qr_url}'
    send_mail(subject, message, 'no-reply@tuapp.com', [user.email])
    
    messages.success(request, 'Se ha enviado un nuevo código QR a tu correo.')
    return redirect('dashboard')

import openpyxl
from openpyxl.styles import Font, Alignment
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.template.loader import get_template

@login_required
def export_logs_excel(request):
    if not request.user.is_superuser:
        return HttpResponse("No autorizado", status=403)
        
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Historial de Logins"
    
    # Encabezados
    headers = ['User', 'Tipo', 'IP', 'Fecha', 'Navegador', 'Latitud', 'Longitud']
    ws.append(headers)
    
    # Estilo encabezados
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Datos
    logs = LoginLog.objects.all().order_by('-timestamp')
    for log in logs:
        ws.append([
            log.user.username,
            log.login_type,
            log.ip_address,
            log.timestamp.strftime('%Y-%m-%d %H:%M'),
            log.user_agent[:50],
            log.latitude,
            log.longitude
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=reporte_logins.xlsx'
    wb.save(response)
    return response

@login_required
def export_intruders_pdf(request):
    if not request.user.is_superuser:
        return HttpResponse("No autorizado", status=403)
        
    attempts = AccessAttempt.objects.all().order_by('-timestamp')
    template = get_template('accounts/intruders_report_pdf.html')
    html = template.render({'attempts': attempts, 'title': 'Reporte de Intrusión'})
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_intrusos.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    return response

def logout_view(request):
    logout(request)
    return redirect('login')


def request_qr_from_login(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        try:
            # Buscamos al usuario real por su username o por su email
            if '@' in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(username=identifier)
                
            # 1. Creamos el Token Nuevo en tu base de datos
            token_obj = QRToken.objects.create(user=user)
            
            # 2. Construimos la URL absoluta apuntando a tu vista 'qr_login_view'
            # (Ajusta 'qr_login' si el name en tu urls.py es diferente)
            qr_url = request.build_absolute_uri(reverse('qr_login')) 
            full_url = f"{qr_url}?token={token_obj.token}"
            
            # 3. Generamos la imagen del código QR con tu configuración HIGH de densidad
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=25,
                border=4,
            )
            qr.add_data(full_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Guardar en el buffer de memoria
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # 4. Configurar y enviar tu correo electrónico con el adjunto
            subject = "Tu Nuevo Código QR de Acceso Seguro"
            message_body = (
                f"Hola {user.username},\n\n"
                f"Has solicitado un nuevo acceso seguro para tu cuenta.\n\n"
                f"Puedes iniciar sesión haciendo clic en el siguiente enlace:\n{full_url}\n\n"
                f"O bien, escanea este nuevo código QR adjunto con la cámara de la aplicación.\n\n"
                f"Recuerda que caducará en 10 minutos o tras su primer uso.\n\n"
                f"Un saludo,\nEl equipo de QRLogin"
            )
            
            email = EmailMessage(
                subject=subject,
                body=message_body,
                from_email="no-reply@tuapp.com",
                to=[user.email],
            )
            email.attach(f"QR_Acceso_{user.username}.png", buffer.read(), "image/png")
            email.send()
            
            messages.success(request, "Se ha enviado un nuevo código QR a tu correo.")
            
        except User.DoesNotExist:
            # Mensaje de error si ponen un usuario que no existe
            messages.error(request, "No se encontró ningún usuario con ese nombre o correo.")
            
    return redirect('login')





@login_required
@csrf_exempt # Para facilitar el envío de datos por POST desde JS sin problemas de token CSRF
def log_salat_query(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            SalatQueryLog.objects.create(
                user=request.user,
                location_name=data.get('title', 'Punto en el Mapa'),
                latitude=str(data.get('lat')),
                longitude=str(data.get('lon'))
            )
            return JsonResponse({'status': 'success', 'message': 'Consulta de Salat registrada con éxito.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)