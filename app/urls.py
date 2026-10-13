from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('termos/', include('termos.urls')),
    path('arquivos/', include('arquivos.urls')),
    path('redesim/', include('redesim.urls')),
    path('denuncias/', include('denuncias.urls')),
    path('', include('home.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('admin/', admin.site.urls),
    path('register/', include('register.urls', namespace='register_view')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
