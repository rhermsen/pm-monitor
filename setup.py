#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='PM-Monitor',
      version='1.0',
      description='Python HTTP wrapper for PM-Monitor',
      author='Ron Hermsen',
      author_email='ronhermsen@gmail.com',
      packages=find_packages(),
      zip_safe=False,
      entry_points={
          'console_scripts': ['pm_monitor=pm_monitor.main:main']
      },
      install_requires=[
         'python-dateutil',
         'flask',
         'flask_table'
      ],
      include_package_data=True,
      package_data={'': ['*/*.html', '*/*.css']},
    )

    