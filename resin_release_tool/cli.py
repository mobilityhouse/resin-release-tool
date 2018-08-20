import click
from .releaser import ResinReleaser


@click.command()
@click.option('--app', prompt='App name', help='Application name')
@click.option('--token', prompt='Resin Token', help='Resin.io auth token')
@click.option('--release', prompt='Release commit hash',
              help='Commit hash of the release in resin to set application')
@click.option('--canary', prompt='Canary commit hash',
              help='Commit hash of the release in resin for canary')
def main(app, token, release, canary):
    resin_releaser = ResinReleaser(token, app, release, canary)
    resin_releaser.set_release()


if __name__ == '__main__':
    main()
