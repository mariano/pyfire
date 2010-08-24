#!/usr/bin/env python

from setuptools import setup

setup(name='pyfire',
	version="0.3.0",
	description="A Campfire API implementation in Python",
	long_description="""\
Pyfire provides an easy to use, full featured implementation of the Campfire API
in Python.""",
	classifiers=[
		"Intended Audience :: Developers",
		"License :: OSI Approved :: MIT License",
		"Natural Language :: English",
		"Programming Language :: Python",
		"Topic :: Internet :: WWW/HTTP",
		"Topic :: Software Development :: Libraries :: Python Modules"
	],
	keywords='python campfire api',
	author='Mariano Iglesias',
	url='http://marianoiglesias.com.ar/tag/pyfire',
	license='MIT',
	include_package_data=True,
	zip_safe=True,
	packages=['pyfire'],
	requires=['twisted (>=10.1.0)']
)
