# Releasing

1. Update the version in these two locations:

    - `docs/source/conf.py`
    - `pyproject.toml`

1. Create a new branch and open a PR on GitHub which will run all actions

1. Apply any fixes to make the actions pass

1. Clean your local directory. This will prevent any files not under source control from being built into the distribution.

   ```bash
   git clean -f -x 
   ```

1. Build the wheel and source distributions:

    ```bash
    python setup.py clean bdist_wheel sdist
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

1. Merge PR 