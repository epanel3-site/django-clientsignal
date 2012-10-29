from django.utils.functional import memoize
from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module

import clientsignal.settings as app_settings

__signalconnection = SortedDict()

def __get_signalconnection(import_path):
    """
    Imports the Tornadio2 socket connection class at the given import
    path.
    """
    def get_class(import_path):
        module, attr = import_path.rsplit('.', 1)
        try:
            mod = import_module(module)
        except ImportError as e:
            raise ImproperlyConfigured('Error importing module %s: "%s"' %
                                       (module, e))

        try:
            ImportedClass = getattr(mod, attr)
        except AttributeError:
            raise ImproperlyConfigured('Module "%s" does not define a "%s" '
                                       'class.' % (module, attr))

        return ImportedClass
        
    SignalConnectionClass = get_class(import_path)
    BaseSignalConnection = get_class(app_settings.CLIENTSIGNAL_BASE_SIGNALCONNECTION)

    if not issubclass(SignalConnectionClass, BaseSignalConnection):
        raise ImproperlyConfigured('Finder "%s" is not a subclass of "%s"' %
                                   (SignalConnectionClass, BaseSignalConnection))

    return SignalConnectionClass

get_signalconnection = memoize(__get_signalconnection, __signalconnection, 1)

