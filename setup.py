from setuptools import find_packages, setup
from setuptools.extension import Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext

setup(
    name='barcode',
    version='2.100',
    packages=['mainwindow',
              ],
    ext_modules=cythonize(
        [
            Extension("m_window",
                      ["mainwindow/m_window.py"]),
            Extension("mainwindow",
                      ["mainwindow/mainwindow.py"]),
            Extension("data",
                      ["data/import_ep.py"]),
            Extension("file_open",
                      ["find_json_file/file_open.py"]),
            Extension("search_json",
                      ["find_json_file/search_json.py"]),
        ],
        build_dir="build_cythonize",
        compiler_directives={
            'language_level': "3",
            'always_allow_keywords': True,
        }
    ),
    cmdclass=dict(
        build_ext=build_ext
    ),
    url='',
    license='',
    author='steffen',
    author_email='',
    description=''
)
