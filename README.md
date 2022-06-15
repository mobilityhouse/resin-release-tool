# resin-release-tool
This tool is to set releases to release groups and canaries in balenaCloud

## Installation
```
pip install resin-release-tool
```

## Build / Run locally
You need poetry to build the project https://python-poetry.org/
```
poetry install
poetry build
poetry run resin-release-tool
etc..
```

## Example usage

### One canary group

Mark relevant devices with device tags with name "release_group" and value "canary" on balenaCloud.

**To deploy a canary commit to them, run:**

```bash
resin-release-tool --app $APP_ID release -c $CANARY_COMMIT -g canary
```

**To deploy said commit to rest of devices, run:**

```bash
resin-release-tool --app $APP_ID release -c $NEW_RELEASE_COMMIT -a
resin-release-tool --app $APP_ID unpin canary
```

(Note: Running the unpin command is not necessary if canary is already on `NEW_RELEASE_COMMIT`, however, without it, it won't track the latest app-wide release.)

### Staggered release with multiple groups

Mark relevant devices with device tags with name "release_group" and value "release_group_1/2/3" on balenaCloud.

**To deploy a commit to all devices in a staggered way:**

(Add appropriate wait or checks between commands as appropriate for your usecase.)

```bash
resin-release-tool --app $APP_ID release -c $NEW_RELEASE_COMMIT -g release_group_1
resin-release-tool --app $APP_ID release -c $NEW_RELEASE_COMMIT -g release_group_2
resin-release-tool --app $APP_ID release -c $NEW_RELEASE_COMMIT -g release_group_3

resin-release-tool --app $APP_ID release -c $NEW_RELEASE_COMMIT -a
resin-release-tool --app $APP_ID unpin release_group_1 release_group_2 release_group_3
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
  show_group_versions  Show the release versions of the devices in release groups
  unpin                Unpins the version of one or more releases
```

# Development

* The config file used by the balena_sdk is located at `$HOME/.balena/balena.cfg` 

To format the code run:  

    black <path to files >


Tests can be run with 

    poetry run pytests


To debug/run commands in pycharm configure `resin_release_tool/cli.py` as the script path and the command you want to  run as parameter (credentials can be added as envs)

## Publishing a new version
### Pre-release steps

* upddate the changelog and run
    ```bash
    make release <version>  # e.g. v0.3.1
    ```
    to update the version in `pyproject.toml`

### Release step
* After merging these changes, tag the commit on master using `git tag <version>`. This must match the new version in the `pyprojct.toml`
* push the new tag to Github `git push origin <version>` this should trigger the `publish-to-pypi` workflow

New versions are uploaded to https://pypi.org/project/resin-release-tool/