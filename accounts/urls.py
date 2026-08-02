from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views


app_name = "accounts"


urlpatterns = [
    path(
        "register/",
        views.register,
        name="register",
    ),

    # Password reset request
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name=(
                "accounts/password_reset.html"
            ),
            email_template_name=(
                "accounts/password_reset_email.html"
            ),
            subject_template_name=(
                "accounts/password_reset_subject.txt"
            ),
            success_url=reverse_lazy(
                "accounts:password_reset_done"
            ),
        ),
        name="password_reset",
    ),

    # Password reset email sent
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name=(
                "accounts/password_reset_done.html"
            ),
        ),
        name="password_reset_done",
    ),

    # Password reset link opened
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name=(
                "accounts/password_reset_confirm.html"
            ),
            success_url=reverse_lazy(
                "accounts:password_reset_complete"
            ),
        ),
        name="password_reset_confirm",
    ),

    # Password successfully changed
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name=(
                "accounts/password_reset_complete.html"
            ),
        ),
        name="password_reset_complete",
    ),

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
        ),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),
]