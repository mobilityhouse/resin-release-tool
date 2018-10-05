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
    """You can set app and token as environment variables,
    using RESIN_APP and RESIN_TOKEN
    """
    ctx.obj = ResinReleaser(token, app)


@cli.command()
@pass_releaser
def info(releaser):
    """Information of the application"""

    info = releaser.get_info()
    rolling = info['should_track_latest_release'] and 'Yes' or 'No'
    info_list = [
        f"App Name: {info['app_name']}",
        f"Device Type: {info['device_type']}",
        f"In Commit: {info['commit']}",
        f"Rolling enabled: {rolling}"]
    click.echo('\n'.join(info_list))


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
    releases = list(releaser.get_releases().values())
    if releases:
        commit = releases[0]['commit']
        releaser.set_app_to_release(commit)
    click.echo("Enabled rolling")


@cli.command()
@pass_releaser
def show_devices_status(releaser):
    """Show the status of the devices in the applications"""

    devices = releaser.get_devices_by_status()

    canaries = ', '.join(
        [c['uuid'][:6] for c in devices['canaries'].values()])
    old_canaries = ', '.join(
        [c['uuid'][:6] for c in devices['old_canaries'].values()])

    rest = list(devices['rest'].values())
    rest_len = len(rest)
    rest_info = ', '.join([c['uuid'][:6] for c in rest[:10]])
    if rest_len > 10:
        rest_info += f'... and {rest_len-10} more'

    click.echo(f'Canaries: {canaries}')
    click.echo(f'Old Canaries: {old_canaries}')
    click.echo(f'Rest of the Devices: {rest_info}')


@cli.command()
@click.argument('release_commit')
@click.argument('canary_commit')
@pass_releaser
@click.pass_context
def release(ctx, releaser, release_commit, canary_commit):
    """Sets release and canary commits"""
    if not releaser.is_valid_commit(release_commit):
        click.echo(f'Invalid release commit: {release_commit}')
        exit(2)
    if not releaser.is_valid_commit(canary_commit):
        click.echo('Invalid canary commit: {canary_commit}')
        exit(2)

    ctx.invoke(info)
    click.echo('Devices:')
    ctx.invoke(show_devices_status)
    click.echo()

    confirm_text = 'Are you sure you want to set '\
        'release/canary to: "%s" "%s"?' % (
            release_commit, canary_commit)
    if not click.confirm(confirm_text):
        click.echo('Cancelled!')
        exit(1)
    releaser.set_release(release_commit, canary_commit)


@cli.command()
@click.option('--count', default=10, help='How many')
@pass_releaser
def releases(releaser, count):
    """Show successful releases of the application"""
    releases = list(releaser.get_releases().values())
    click.echo(f'Latest {count} releases:')
    for release in releases[:count]:
        click.echo(f'{release["end_timestamp"]} {release["commit"]}')


if __name__ == '__main__':
    cli()
