from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

handler403 = "novamart_project.views.error_403"
handler404 = "novamart_project.views.error_404"
handler500 = "novamart_project.views.error_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("catalog.urls")),
    path("cart/", include("cart.urls")),
    path("", include("orders.urls")),
    path("dashboard/", include("dashboard.urls")),
]

if settings.DEBUG:
    # Development-only media serving. In production, let the web server
    # (nginx, Apache, a CDN or object storage) serve MEDIA_ROOT instead.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
