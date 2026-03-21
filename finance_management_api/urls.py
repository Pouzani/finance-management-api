from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('categories.urls')),
    path('api/', include('transactions.urls')),
    path('api/', include('goals.urls')),
    path('api/', include('analytics.urls')),
    path('api/', include('budgets.urls')),
]
