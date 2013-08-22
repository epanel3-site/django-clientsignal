# Create your views here.
import signals

from django.template.response import TemplateResponse

def simpleview(request):
    return TemplateResponse(request, 'index.html', {})

