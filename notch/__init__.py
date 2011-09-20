# This package is a namespace package using setuptools

import pkg_resources
pkg_resources.declare_namespace(__name__)
del pkg_resources