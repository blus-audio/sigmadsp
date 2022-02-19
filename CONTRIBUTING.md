# Contributing and checking your code

Coding style in this repository is checked by means of [pre-commit](https://pre-commit.com/), and a selection of useful tools.
Before committing your changes, please install pre-commit

```bash
python3 -m pip install pre-commit
```

and install the git hooks with

```bash
pre-commit install
```

Changes are then checked against the coding style toolchain upon committing.
You may also run `pre-commit` on all files in the repository with

```bash
pre-commit run --all-files
```

before committing.
