# -*- coding: utf-8 -*-

# Losely based on django.core.management.commands.runserver

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
import tornado.httpserver
from sockjs.tornado import SockJSRouter

from clientsignal import settings as app_settings
from clientsignal import SignalConnection
from clientsignal.utils import get_class_or_func

# from tornado import httpserver, wsgi, ioloop, web
# from tornado.web import Application
# from tornado.web import FallbackHandler
# from tornado.web import StaticFileHandler
# from tornado.wsgi import WSGIContainer

DEFAULT_PORT = "8000"

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--reload', 
            action='store_true',
            dest='use_reloader', 
            default=False,
            help="Use code change auto-reloader."),
        make_option('--django', 
            action='store_true',
            dest='use_django', 
            default=False,
            help="Serve the full Django application."),
        make_option('--static', 
            action='store_true',
            dest='use_static', 
            default=False,
            help="Serve static files (requires --django)."),
    )
    help = "Starts a Tornado/SockJS Socket Server."
    args = '[optional port number] (multiple starts multiple servers)'

    requires_model_validation = False

    def handle(self, *ports, **options):
        if settings.DEBUG:
            import logging
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)

        use_django = options.get('use_django', False)
        if use_django and not ports:
            ports = [DEFAULT_PORT]
        elif not ports:
            self.stderr.write("Please specify a port or --django to run on the default port.\n")
            sys.exit(0)

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
        import itertools

        shutdown_message = options.get('shutdown_message', '')
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'
        
        self.stdout.write("Validating models...\n\n")
        self.validate(display_num_errors=True)
        translation.activate(settings.LANGUAGE_CODE)

        # Run Django from Tornado
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

        base_port = self.ports[0]

        # Create routers for each connection defined in the Django
        # settings file.
        routers = [SockJSRouter(get_class_or_func(conn), url) 
                for url, conn in app_settings.CLIENTSIGNAL_CONNECTIONS.items()]
        socket_urls = list(itertools.chain.from_iterable([r.urls for r in routers]))
        tornado_urls = socket_urls 

        use_django = options.get('use_django', False)
        if use_django:
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

            tornado_urls = tornado_urls + [
                        (r'.*', 
                            tornado.web.FallbackHandler, 
                            {'fallback': django_container}),
                    ]

        try:
            application = tornado.web.Application(tornado_urls)
            io_loop = tornado.ioloop.IOLoop.instance()
            server = tornado.httpserver.HTTPServer(application, 
                    io_loop=io_loop)

            # Add the remainder of ports.
            for port in self.ports:
                server.listen(port)

            self.stdout.write((
                "%(started_at)s\n"
                "Django version %(version)s, using settings %(settings)r\n"
                "Socket Server is running on ports %(ports)s\n"
            ) % {
                "started_at": datetime.now().strftime('%B %d, %Y - %X'),
                "version": self.get_version(),
                "settings": settings.SETTINGS_MODULE,
                "ports": ", ".join(self.ports),
            })

            self.stdout.write((
                "Quit the server with %(quit_command)s.\n"
            ) % {
                "quit_command": quit_command,
            })

            io_loop.start()


        except KeyboardInterrupt:
            if shutdown_message:
                self.stdout.write(shutdown_message)
            sys.exit(0)


       

