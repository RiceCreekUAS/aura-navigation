#!/usr/bin/env python

from setuptools import setup, Extension

setup(name='navigation',
      version='1.0',
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
                      libraries=['boost_python']),
            Extension('nav.wgs84',
                      define_macros=[('HAVE_BOOST_PYTHON', '1')],
                      sources=['src/nav_common/wgs84.cxx'],
                      libraries=['boost_python']),
            Extension('nav.EKF15_double',
                      define_macros=[('HAVE_BOOST_PYTHON', '1')],
                      sources=['src/nav_eigen_double/EKF_15state.cxx',
                               'src/nav_common/nav_functions_double.cxx'],
                      libraries=['boost_python'],
                      depends=['src/nav_eigen_double/EKF_15state.hxx',
                               'src/nav_common/nav_functions_double.hxx']),
            Extension('nav.EKF15_mag',
                      define_macros=[('HAVE_BOOST_PYTHON', '1')],
                      sources=['src/nav_eigen_mag/EKF_15state_mag.cxx',
                               'src/nav_common/nav_functions_double.cxx',
                               'src/nav_common/coremag.c'],
                      libraries=['boost_python'],
                      depends=['src/nav_eigen_mag/EKF_15state_mag.hxx',
                               'src/nav_common/nav_functions_double.hxx',
                               'src/nav_common/coremag.h']),
            Extension('nav.EKF15_float',
                      define_macros=[('HAVE_BOOST_PYTHON', '1')],
                      sources=['src/nav_eigen_float/EKF_15state.cxx',
                               'src/nav_eigen_float/nav_functions_float.cxx'],
                      libraries=['boost_python'],
                      depends=['src/nav_eigen_float/EKF_15state.hxx',
                               'src/nav_eigen_float/nav_functions_float.hxx']),
            Extension('nav.EKF15_sep',
                      define_macros=[('HAVE_BOOST_PYTHON', '1')],
                      sources=['src/nav_eigen_sep/EKF_15state.cxx',
                               'src/nav_eigen_sep/nav_functions_float.cxx'],
                      libraries=['boost_python'],
                      depends=['src/nav_eigen_sep/EKF_15state.hxx',
                               'src/nav_eigen_sep/nav_functions_float.hxx']),
            Extension('nav.openloop',
                      define_macros=[('HAVE_BOOST_PYTHON', '1')],
                      sources=['src/nav_openloop/openloop.cxx',
                               'src/nav_openloop/glocal.cxx',
                               'src/nav_common/nav_functions_double.cxx'],
                      libraries=['boost_python'],
                      depends=['src/nav_openloop/openloop.hxx',
                               'src/nav_openloop/glocal.hxx',
                               'src/nav_common/nav_functions.hxx'])
      ],
     )
