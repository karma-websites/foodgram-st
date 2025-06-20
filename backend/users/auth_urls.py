from django.urls import path, include

# api/auth/
urlpatterns = [
    path("", include("djoser.urls")),               # регистрация, активация,
    path("", include("djoser.urls.authtoken")),     # /token/login/ и /logout/
]