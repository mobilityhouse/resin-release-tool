import click
from .releaser import ResinReleaser


@click.command()
@click.option('--app', prompt='App name', help='Application name')
@click.option('--token', prompt='Resin Token', help='Resin.io auth token')
@click.option('--release', prompt='Release commit hash',
              help='Commit hash of the release in resin to set application')
@click.option('--canary', prompt='Canary commit hash',
              help='Commit hash of the release in resin for canary')
@click.option('--releases', is_flag=True, help='Show last releases')
def main(app, token, release, canary, releases):
    resin_releaser = ResinReleaser(token, app, release, canary)
    if releases:
        resin_releaser.get_releases()
    else:
        resin_releaser.set_release()


if __name__ == '__main__':
    main()
