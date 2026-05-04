from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Shop App
    path('', include('shop.urls')),

    # Django Allauth (LOGIN / LOGOUT / GOOGLE)
    path('accounts/', include('allauth.urls')),
]