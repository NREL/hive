# Building the Docs

## install sphinx

```bash
conda install sphinx
pip install sphinx-autodoc-typehints
pip isntall recommonmark
pip install sphinx-rtd-theme
```

## regenerating the api-docs

navigate to the hive repo and run:

```bash
sphinx-apidoc -o hive/docs/source hive/hive
```

## building html

```bash
cd hive/docs
make html
cp -r build/html/* <path/to/hive-docs>
```

