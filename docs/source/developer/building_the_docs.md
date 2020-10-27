# building the docs

install sphinx, themes and extensions

```
conda install sphinx
pip install sphinx-rtd-theme
pip install recommonmark
pip install sphinx-markdown-tables
pip install sphinx-autodoc-typehints
```

run build script
```bash
cd hive/docs
bash build_docs.sh
```

or, manually

```bash
cd hive/docs

cp ../README.md source/

make html

python emojize.py

cp -r build/html/* <path/to/hive-doc/repo> 

cd <path/to/hive-doc/repo> 

git add *
git commit -m "publish docs"
git push
```


