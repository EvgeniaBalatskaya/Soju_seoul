from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('booking.urls')),  # ← только этот include
    path('accounts/login/', RedirectView.as_view(url='/auth/login/', permanent=False)),
]
