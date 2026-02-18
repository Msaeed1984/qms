from django.contrib import admin
from django.urls import path, include

# لعرض ملفات media أثناء التطوير
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # لوحة تحكم Django
    path('admin/', admin.site.urls),

    # =========================
    # Core (login + home + quality)
    # =========================
    path('', include('core.urls')),

    # =========================
    # Accounts (إن وجد صفحات لاحقًا)
    # =========================
    path('accounts/', include('accounts.urls')),

    # =========================
    # Documents module
    # =========================
    path('documents/', include('documents.urls')),
]


# =========================
# Media files (PDFs) أثناء التطوير فقط
# =========================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)