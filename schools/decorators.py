from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import SchoolAdministrator


def school_administrator_required(view_function):
    """
    Allow access only to active school administrators
    connected to an active school.
    """

    @login_required
    @wraps(view_function)
    def wrapper(request, *args, **kwargs):
        school_administrator = (
            SchoolAdministrator.objects
            .select_related("school")
            .filter(
                user=request.user,
                is_active=True,
                school__is_active=True,
            )
            .first()
        )

        if school_administrator is None:
            messages.error(
                request,
                "You do not have permission to access the school portal.",
            )

            return redirect(
                "accounts:dashboard"
            )

        request.school_administrator = school_administrator
        request.school = school_administrator.school

        return view_function(
            request,
            *args,
            **kwargs,
        )

    return wrapper