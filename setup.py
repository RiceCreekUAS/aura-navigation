#!/usr/bin/python3

from setuptools import setup, Extension

setup(name='navigation',
      version='1.1',
      description='Navigation Tools',
      author='Curtis L. Olson',
      author_email='curtolson@flightgear.org',
      url='https://github.com/AuraUAS',
      #py_modules=['props', 'props_json', 'props_xml'],
      #package_dir = {'': 'lib'},
      packages=['nav'],
      #ext_package='nav',
      ext_modules=[
          Extension('nav.structs',
                    define_macros=[('HAVE_BOOST_PYTHON', '1')],
                    sources=['src/nav_common/structs.cxx'],
                    libraries=['boost_python3']),
          Extension('nav.EKF15_mag',
                    define_macros=[('HAVE_BOOST_PYTHON', '1')],
                    sources=['src/nav_ekf15_mag/EKF_15state.cxx',
                             'src/nav_common/nav_functions_float.cxx',
                             'src/nav_common/coremag.c'],
                    libraries=['boost_python3'],
                    depends=['src/nav_ekf15_mag/EKF_15state.hxx',
                             'src/nav_common/constants.hxx',
                             'src/nav_common/nav_functions_float.hxx',
                             'src/nav_common/coremag.h']),
          Extension('nav.EKF15',
                    define_macros=[('HAVE_BOOST_PYTHON', '1')],
                    sources=['src/nav_ekf15/EKF_15state.cxx',
                             'src/nav_common/nav_functions_float.cxx'],
                    libraries=['boost_python3'],
                    depends=['src/nav_ekf15/EKF_15state.hxx',
                             'src/nav_common/constants.hxx',
                             'src/nav_common/nav_functions_float.hxx']),
          Extension('nav.openloop',
                    define_macros=[('HAVE_BOOST_PYTHON', '1')],
                    sources=['src/nav_openloop/openloop.cxx',
                             'src/nav_openloop/glocal.cxx',
                             'src/nav_common/nav_functions_float.cxx'],
                    libraries=['boost_python3'],
                    depends=['src/nav_openloop/openloop.hxx',
                             'src/nav_openloop/glocal.hxx',
                             'src/nav_common/nav_functions_float.hxx'])
      ],
     )
