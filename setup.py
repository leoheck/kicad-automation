#!/usr/bin/python3

from distutils.core import setup

setup(
    name='kicad-automation-scripts',
    version='1.0.0',
    description='KiCad Automation Scripts',
    long_description='Uses Kicad EEschema and PCBNew to automate some tasks.',
    author='Scott Bezek, Salvador E. Tropea',
    author_email='leoheck@gmail.com',
    url='https://github.com/leoheck/kicad-automation-scripts/',
    packages=['kicad_auto'],
    package_dir={'kicad_auto': 'kicad_auto'},
    scripts=[
        'src/eeschema_do',
        'src/pcbnew_print_layers',
        'src/pcbnew_run_drc'
    ],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache License 2.0',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
    ],
    platforms   = 'POSIX',
    license     = 'Apache License 2.0'
)
