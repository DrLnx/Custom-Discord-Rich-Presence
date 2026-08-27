# Releasing

Everything is automated from a tag. The two one-time setups are below.

## One-time: GitHub

```bash
gh auth login
gh repo create n3xt-agency/drpc --public --source=. --push
```

If the repo lives somewhere else, update the three `[project.urls]` entries in
`pyproject.toml` and the install URLs in `README.md` to match.

## One-time: PyPI trusted publishing

No API token is stored anywhere — PyPI verifies the workflow's OIDC identity.

1. Create the project owner account on <https://pypi.org>.
2. Go to **Your projects → Publishing → Add a new pending publisher** and enter:
   - PyPI project name: `discord-rpc-cli`
   - Owner: `n3xt-agency`
   - Repository: `drpc`
   - Workflow name: `release.yml`
   - Environment name: `pypi`
3. In the GitHub repo, create an environment named `pypi`
   (**Settings → Environments → New environment**). Add a required reviewer if
   you want a manual gate before anything reaches PyPI.

## Cutting a release

```bash
# 1. bump the version in the two places that carry it
#    src/drpc/cli.py  __version__
#    pyproject.toml   version
# 2. write the entry in CHANGELOG.md
git commit -am "drpc 1.1.0"
git tag v1.1.0
git push origin main --tags
```

The `release` workflow then:

1. builds a single-file executable on Linux and Windows, and smoke-tests each
   one (`--version`, `path`) before accepting it;
2. builds the sdist and wheel;
3. publishes to PyPI through the `pypi` environment;
4. opens a **draft** GitHub release with all four artifacts attached and
   generated notes.

Review the draft, then press publish.

## Checking a build without releasing

```bash
pip install -e ".[build]"
pyinstaller --clean --noconfirm drpc.spec
./dist/drpc --version          # dist\drpc.exe on Windows

python -m build && twine check dist/*
```

`workflow_dispatch` also runs the binary and distribution jobs on demand; the
publish steps are gated on a `v*` tag, so a manual run only produces artifacts.
