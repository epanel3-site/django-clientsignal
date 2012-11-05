# -*- coding: utf-8 -*-

# Losely based on django.core.management.commands.runserver and 
# django-tornadio management command

import sys
import os.path
import logging
from datetime import datetime
from optparse import make_option

from django.conf import settings

from django.core.management.base import BaseCommand, CommandError
from django.core.wsgi import get_wsgi_application

from django.utils import autoreload

import tornado
import tornado.wsgi
import tornadio2

from clientsignal import settings as app_settings
from clientsignal import SignalConnection
from clientsignal.utils import get_signalconnection

# from tornado import httpserver, wsgi, ioloop, web
# from tornado.web import Application
# from tornado.web import FallbackHandler
# from tornado.web import StaticFileHandler
# from tornado.wsgi import WSGIContainer
# from tornadio2 import TornadioRouter
# from tornadio2 import SocketServer

DEFAULT_PORT = "8000"

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--reload', 
            action='store_true',
            dest='use_reloader', 
            default=False,
            help="Use code change auto-reloader."),
        make_option('--static', 
            action='store_true',
            dest='use_static', 
            default=False,
            help="Serve static files."),
        
    )
    help = "Starts a Tornado/TornadIO2 Socket Server."
    args = '[optional port number] (multiple starts multiple servers)'

    requires_model_validation = False

    def handle(self, *ports, **options):
        if settings.DEBUG:
            import logging
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)

        # if len(ports) > 2:
        #     raise CommandError('Usage is runtornadio2 %s' % self.args)

        if not ports:
            ports = [DEFAULT_PORT]
        self.ports = ports

        self.run(**options)


    def run(self, **options):
        """
        Runs the server, using the autoreloader if needed
        """
        use_reloader = options.get('use_reloader', False)

        if use_reloader:
            autoreload.main(self.inner_run, (), options)
        else:
            self.inner_run(**options)


    def inner_run(self, **options):
        from django.utils import translation

        shutdown_message = options.get('shutdown_message', '')
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'
        
        self.stdout.write("Validating models...\n\n")
        self.validate(display_num_errors=True)
        self.stdout.write((
            "%(started_at)s\n"
            "Django version %(version)s, using settings %(settings)r\n"
            "Development server is running on ports %(ports)s\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "started_at": datetime.now().strftime('%B %d, %Y - %X'),
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "ports": ", ".join(self.ports),
            "quit_command": quit_command,
        })

        translation.activate(settings.LANGUAGE_CODE)

        # Run Django from Tornado
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

        base_port = self.ports[0]

        django_handler = get_wsgi_application()

        use_static = options.get('use_static', False)
        if use_static:
            # (r'/static/(.*)', 
            #     tornado.web.StaticFileHandler, 
            #     {'path': static_path}),
            # XXX: Use tornado for this instead of Django.
            from django.contrib.staticfiles.handlers import StaticFilesHandler
            django_handler = StaticFilesHandler(django_handler)
            
        django_container = tornado.wsgi.WSGIContainer(django_handler)

        ConnectionClass = get_signalconnection(
                app_settings.CLIENTSIGNAL_MULTIPLEXED_CONNECTION)
        router = tornadio2.TornadioRouter(ConnectionClass, {
            'enabled_protocols': [
                    'websocket',
                    'xhr-polling',
                    'htmlfile'
            ]})

        try:
            application = tornado.web.Application(router.urls + [
                        (r'.*', 
                            tornado.web.FallbackHandler, 
                            {'fallback': django_container}),
                    ],

                    # The TornadIO2 SocketServer wrapper for Tornado
                    # will take care of the initial port. The first port
                    # will be the only one used for socket.io.
                    # XXX: Find a way to use more than one port for
                    # socket.io?
                    socket_io_port = base_port,
            )

            io_loop = tornado.ioloop.IOLoop.instance()
            server = tornadio2.SocketServer(application, 
                    io_loop = io_loop, auto_start = False) 

            # Add the remainder of ports.
            for port in self.ports[1:]:
                logging.info('Adding tornadio server on port \'%s\'',
                             port)
                server.listen(port)

            io_loop.start()

        except KeyboardInterrupt:
            if shutdown_message:
                self.stdout.write(shutdown_message)
            sys.exit(0)


       
