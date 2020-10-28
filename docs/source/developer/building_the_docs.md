# building the docs

the hive docs source code lives in the hive repository under `hive.docs.source`

these are rendered to html and pushed to https://github.nrel.gov/MBAP/hive-docs

the hive-docs repo publishes the static html files to https://github.nrel.gov/pages/MBAP/hive-docs/

install sphinx, themes and extensions

```
pip install sphinx
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

get hive-docs repo

```bash
git clone https://github.nrel.gov/MBAP/hive-docs.git
```

run publish script
```bash
bash publish_docs.sh
```

or, manually

```bash
cd hive/docs

cp ../README.md source/
sed "s|docs/source/||" source/README.md > source/tmp_README.md
mv source/tmp_README.md source/README.md

make html

python emojize.py

cp -r build/html/* <path/to/hive-doc/repo> 

cd <path/to/hive-doc/repo> 

git add *
git commit -m "publish docs"
git push
```


