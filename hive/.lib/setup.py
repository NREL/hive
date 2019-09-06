from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
from Cython.Build import cythonize

ext_modules=[
    Extension(
            "c_haversine",
            ["c_haversine.pyx"],
            libraries=["m"],
            extra_compile_args = ["-fopenmp"],
            extra_link_args = ['-lomp']
            )
]

setup(
    name = "c_haversine",
    cmdclass = {'build_ext': build_ext},
    ext_modules = ext_modules
)
