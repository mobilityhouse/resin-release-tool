import click
from .releaser import ResinReleaser


# get releaser object from the context
pass_releaser = click.make_pass_decorator(ResinReleaser)


@click.group()
@click.option('--token', required=True, envvar='RESIN_TOKEN',
              metavar='TOKEN', help='Resin.io auth token')
@click.option('--app', required=True, envvar='RESIN_APP',
              metavar='APP_ID', help='Resin App name')
@click.pass_context
def cli(ctx, app, token):
    """You can set app and token as an environment variable,
    using RESIN_APP and RESIN_TOKEN
    """
    ctx.obj = ResinReleaser(token, app)


@cli.command()
@pass_releaser
def disable_rolling(releaser):
    """Disables rolling releases in the application"""
    releaser.disable_rolling()
    click.echo("Disabled rolling")


@cli.command()
@pass_releaser
def enable_rolling(releaser):
    """Enables rolling releases in the application"""
    releaser.enable_rolling()
    click.echo("Enabled rolling")


@cli.command()
@click.argument('release_commit')
@click.argument('canary_commit')
@pass_releaser
def release(releaser, release_commit, canary_commit):
    """Sets release and canary commits"""
    releaser.set_release(release_commit, canary_commit)


@cli.command()
@pass_releaser
def releases(releaser):
    """Show success releases of the application"""
    releaser.get_releases()


if __name__ == '__main__':
    cli()
