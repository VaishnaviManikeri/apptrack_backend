from django.urls import path

from .auth_views import CurrentUserView, LoginView, PublicTokenRefreshView, RegisterView
from .views import (
    ApiRootView,
    ApplicationDetailView,
    ApplicationListCreateView,
    HealthView,
)


urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("health/", HealthView.as_view(), name="health"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", PublicTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path(
        "applications/",
        ApplicationListCreateView.as_view(),
        name="application-list-create",
    ),
    path(
        "applications/<str:application_id>/",
        ApplicationDetailView.as_view(),
        name="application-detail",
    ),
]
