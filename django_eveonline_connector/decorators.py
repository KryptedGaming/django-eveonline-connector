from django.urls import resolve
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django_eveonline_connector.models import EveScope

def required_scopes(scopes=[]):
    def _method_wrapper(view_method):
        def wrap(request, *args, **kwargs):
            if not request.user.primary_evecharacter:
                messages.error(request, "You are missing an EVE Online character.")
                return redirect('/')
            redirect_user = False 
            for scope in scopes: 
                scope = EveScope.objects.get_or_create(name=scope)[0]
                if scope not in request.user.primary_evecharacter.character.token.scopes.all():
                    redirect_user = True 
                    request.user.primary_evecharacter.character.token.requested_scopes.add(scope)
            if redirect_user:
                messages.warning(request, "You are missing required scopes. Check your token and try again.")
                return redirect("/")
            return view_method(request, *args, **kwargs)
        return wrap 
    return _method_wrapper
