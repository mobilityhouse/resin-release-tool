# resin-release-tool
This tool is to set release canary in balena.io

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

  You can set app and token as environment variables, using RESIN_APP and
  RESIN_TOKEN

Options:
  --token TOKEN  balenaCloud auth token  [required]
  --app APP_ID   balenaCloud app ID  [required]
  --help         Show this message and exit.

Commands:
  disable_rolling      Disables rolling releases in the application
  enable_rolling       Enables rolling releases in the application
  info                 Information of the application
  release              Sets release commits for a given release or app
  releases             Show successful releases of the application
  show_devices_status  Show the status of the devices in the app
  unpin                Unpins the version of one or more releases
```
