# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from os.path import dirname, join

setup(
    name='django-clientsignal',
    version='0.2',
    author='Will Barton',
    author_email='willbarton@gmail.com',
    description='TornadIO2-based mechanism for sending and receiving Django signals as socket.io client-side events.',
    long_description=open('README.txt').read(),
    url='http://github.com/gulielmus/django-clientsignal',
    install_requires=["tornadio2", "redis", "tornado-redis"],
    include_package_data=True,
    package_data={'clientsignal':['static/clientsignal/js/*',],},
    packages=find_packages(),
    license='BSD',
)

