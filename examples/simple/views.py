# Create your views here.
import signals

from django.template.response import TemplateResponse

def simpleview(request):
    signals.pong.send(sender=None, pong="Ponged")
    return TemplateResponse(request, 'index.html', {})

