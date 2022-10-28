# Releasing

1. Update the version in these two locations:

- `docs/source/conf.py`
- `pyproject.toml`

1. Build the wheel and source distributions:

```bash
python setup.py bdist_wheel sdist
```

1. Upload to Test PyPi

```bash
twine upload -r testpypi dist/* --verbose
```

1. Upload to PyPi

```bash
twine upload dist/*
```

1. Add a git tag

```bash
git tag -a v<major>.<minor>.<patch> -m "version <major>.<minor>.<patch>"
git push origin <tagname>
```
