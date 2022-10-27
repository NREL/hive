# building the docs

the hive docs source code lives in the hive repository under `hive.docs.source`

install sphinx, themes and extensions

```bash
pip install sphinx
pip install sphinx-rtd-theme
pip install recommonmark
pip install sphinx-markdown-tables
pip install sphinx-autodoc-typehints
```

build the docs

```bash
cd hive/docs

make html
```
