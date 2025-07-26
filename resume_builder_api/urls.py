from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

def root_view(request):
    return HttpResponse("Welcome to your Resume API!")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('resume.urls')),  # Include the resume app's URLs
    path('', root_view),  # Root URL
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)