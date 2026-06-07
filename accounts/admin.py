from django.contrib import admin
from .models import QRToken, LoginLog, AccessAttempt, SalatQueryLog
from django.utils.html import format_html


@admin.register(QRToken)
class QRTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expires_at', 'is_used', 'is_valid_status')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'token')
    readonly_fields = ('created_at',)
    
    def is_valid_status(self, obj):
        return obj.is_valid()
    is_valid_status.boolean = True
    is_valid_status.short_description = '¿Válido?'

@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_type', 'ip_address', 'timestamp', 'user_agent_short')
    list_filter = ('login_type', 'timestamp')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('timestamp', 'user_agent', 'ip_address')

    def user_agent_short(self, obj):
        return obj.user_agent[:50] + "..." if obj.user_agent else "-"
    user_agent_short.short_description = 'Browser/Device'

@admin.register(AccessAttempt)
class AccessAttemptAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'ip_address', 'was_successful', 'photo_preview')
    list_filter = ('was_successful', 'timestamp')
    readonly_fields = ('timestamp', 'ip_address', 'user_agent', 'photo')

    def photo_preview(self, obj):
        if obj.photo:
            from django.utils.html import format_html
            return format_html('<img src="{}" style="height: 50px; border-radius: 5px;"/>', obj.photo.url)
        return "No Foto"
    photo_preview.short_description = 'Evidencia'


# 👇 NUEVO: Registro del modelo de consultas del mapa de Salat
@admin.register(SalatQueryLog)
class SalatQueryLogAdmin(admin.ModelAdmin):
    # Columnas que se mostrarán en la lista general del admin
    list_display = ('user', 'location_name', 'latitude', 'longitude', 'timestamp_formated')
    
    # Filtros laterales rápidos por fecha y lugar seleccionado
    list_filter = ('timestamp', 'location_name')
    
    # Buscador inteligente por nombre de usuario y nombre del sitio pulsado
    search_fields = ('user__username', 'location_name')
    
    # Evita que el administrador edite las coordenadas a mano para mantener la integridad de la auditoría
    readonly_fields = ('timestamp', 'user', 'location_name', 'latitude', 'longitude')

    # Formateo amigable para la fecha en la lista
    def timestamp_formated(self, obj):
        return obj.timestamp.strftime("%d %b %Y, %H:%M")
    timestamp_formated.short_description = 'Fecha de Consulta'