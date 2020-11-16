import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-eveonline-connector',
    version=__import__('django_eveonline_connector').__version__,
    packages=find_packages(),
    include_package_data=True,
    license='MIT License',
    description='EVE Online integration for SSO, characters, corporations, alliances, and their respective data.',
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://github.com/KryptedGaming/django-eveonline-connector',
    author='porowns',
    author_email='porowns@gmail.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=[
        'Django==2.2.13',
        'esipy==1.0.0',
        'celery>=4.3.0',
        'django_datatables_view==1.19.1',
    ]
)
