"""
URL configuration for taskmanager_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from core.views import CreateSuperUserView, RegisterView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    path('create-superuser/', CreateSuperUserView.as_view(), name='create-superuser'),
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html')),
    path('sample/', TemplateView.as_view(template_name='sample.html'), name='sample_page'),
    path('sample/sample2/', TemplateView.as_view(template_name='sample2.html'), name='sample_page2'),
    path('api/', include('core.urls')),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/register/', RegisterView.as_view(), name='register')
]
