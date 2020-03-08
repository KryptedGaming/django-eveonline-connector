from django.shortcuts import render, redirect
from django_eveonline_connector.models import EveCorporation
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required

import logging
logger = logging.getLogger(__name__)

@login_required
@permission_required('django_eveonline_connector.view_evecorporation', raise_exception=True)
def view_corporations(request):
    return render(request, 'django_eveonline_connector/adminlte/corporations/list_corporations.html', context={
        'corporations': EveCorporation.objects.all()
    })
