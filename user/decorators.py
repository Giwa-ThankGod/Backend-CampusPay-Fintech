from django.http import HttpResponse
from django.shortcuts import redirect

from rest_framework.response import Response
from rest_framework import status

def unauthorised_user(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            return
        else:
            return view_func(request, *args, **kwargs)
    return wrapper_func

def roles_required(roles):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):
            if any(getattr(request.user, role) for role in roles):
                return view_func(request, *args, **kwargs)
            else:
                return Response(
                    {
                        "status": False,
                        "message": "User is not authorized to access this endpoint."
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
        return wrapper_func
    
    return decorator