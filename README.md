# resin-release-tool
This tool is to set release canary in resin.io

## Installation
```
pip install resin-release-tool
```

## Build / Run locally
You need poetry to build the project https://poetry.eustace.io/
```
poetry install
poetry build
poetry run resin-release-tool
etc..
```


## Usage
```
Usage: resin-release-tool [OPTIONS] COMMAND [ARGS]...

  You can set app and token as an environment variable, using RESIN_APP and
  RESIN_TOKEN

Options:
  --token TOKEN  Resin.io auth token  [required]
  --app APP_ID   Resin App name  [required]
  --help         Show this message and exit.

Commands:
  disable_rolling      Disables rolling releases in the application
  enable_rolling       Enables rolling releases in the application
  info                 Information of the application
  release              Sets release and canary commits
  releases             Show success releases of the application
  show_devices_status  Enables rolling releases in the application
```
