from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),

    # Auth
    path("login/", views.QMSLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Quality Center
    path("quality/", views.quality, name="quality"),
]