# -*- coding: utf-8 -*-

from os.path import dirname, join
from setuptools import setup, find_packages

setup(
    name='django-clientsignal',
    version='0.1',
    author='Will Barton',
    author_email='willbarton@gmail.com',
    description=('TornadIO2-based mechanism for sending and receiving Django signals as socket.io client-side events.'),
    long_description=open('README.txt').read(),
    url='http://github.com/gulielmus/django-clientsignal',
    py_modules=['clientsignal',],
    install_requires=["tornadio2",],
    zip_safe=False,
    include_package_data=True,
    package_data={'clientsignal':['static/clientsignal/js/*',],},
    packages=find_packages(),
    license='BSD',
)

