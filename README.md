# balena-release-tool
This tool is to set release canary in Balena.io

## Build / Run locally
You need poetry to build the project https://poetry.eustace.io/
```
poetry install
poetry build
poetry run resin-release-tool
etc..
```

## Installation(pre built)
TODO: we need to add circleci and create pypi/github releases

```
pip install https://github.com/mobilityhouse/resin-release-tool/releases/download/0.1.0/resin_release_tool-0.1.0-py3-none-any.whl
```

## Usage
```
Usage: balena-release-tool [OPTIONS]

Options:
  --app TEXT      Application name
  --token TEXT    Balena.io auth token
  --release TEXT  Commit hash of the release in Balena to set application
  --canary TEXT   Commit hash of the release in Balena for canary
  --releases      Show last releases
  --help          Show this message and exit.
```
