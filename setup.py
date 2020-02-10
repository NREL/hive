from setuptools import setup, find_packages
from os import path

# Get the long description from the README file
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="nrel_hive",
    version="0.4.1",
    description=
    "HIVE is a mobility services research platform developed by the Mobility and Advanced Powertrains (MBAP) group at the National Renewable Energy Laboratory in Golden, Colorado, USA.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.nrel.gov/MBAP/hive",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering"
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "h3>=3.4.3",
        "immutables>=0.11",
        "PyYAML>=5.1",
        "haversine>=2.1",
        "numpy>=1.17"
    ],
    include_package_data=True,
    package_data={
        "hive.resources": ["*"]
    },
    entry_points={
        'console_scripts': ['hive=hive.app.run:run'],
    },
    author="National Renewable Energy Laboratory",
    author_email="Reinicke, Nicholas <Nicholas.Reinicke@nrel.gov>",
    license="Copyright ©2019 Alliance for Sustainable Energy, LLC All Rights Reserved",
    keywords="transportation simulation ride-hail data-driven agent-based model ABM"
)