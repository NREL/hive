from os import path

from setuptools import setup, find_packages

# Get the long description from the README file
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()
with open(path.join(here, 'LICENSE'), encoding='utf-8') as f:
    notice = f.read()

setup(
    name="nrel.hive",
    version="0.8.5",
    description=
    "HIVE is a mobility services research platform developed by the Mobility and Advanced Powertrains (MBAP) group at the National Renewable Energy Laboratory in Golden, Colorado, USA.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/NREL/hive",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering"
    ],
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "immutables",
        "numpy",
        "pandas",
        "networkx",
        "PyYAML",
        "tqdm",
        "h3>=3.7.1",
        "scipy",
        "returns",
    ],
    extras_require={
        "dev": ["pytest", "black"],
        "docs": [
            "sphinx",
            "sphinx-autoapi",
            "sphinx-rtd-theme",
            "sphinxemoji",
            "recommonmark",
            "myst-parser"
            "sphinx-markdown-tables",
            "sphinx-autodoc-typehints"

        ]
    },
    include_package_data=True,
    package_data={
        "nrel.hive.resources": ["*"]
    },
    entry_points={
        'console_scripts': [
            'hive=nrel.hive.app.run:run',
            'hive-batch=nrel.hive.app.run_batch:run',
        ],
    },
    author="National Renewable Energy Laboratory",
    author_email="Reinicke, Nicholas <Nicholas.Reinicke@nrel.gov>",
    license=notice,
    keywords="transportation simulation ride-hail data-driven agent-based model ABM"
)
