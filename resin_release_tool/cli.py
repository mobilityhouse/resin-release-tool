import click
from .releaser import BalenaReleaser


# get releaser object from the context
pass_releaser = click.make_pass_decorator(BalenaReleaser)


@click.group()
@click.option(
    "--token",
    required=True,
    envvar="RESIN_TOKEN",
    metavar="TOKEN",
    help="balenaCloud auth token",
)
@click.option(
    "--app",
    required=True,
    envvar="RESIN_APP",
    metavar="APP_ID",
    help="balenaCloud app ID",
)
@click.pass_context
def cli(ctx, app, token):
    """You can set app and token as environment variables,
    using RESIN_APP and RESIN_TOKEN
    """
    ctx.obj = BalenaReleaser(token, app)


@cli.command()
@pass_releaser
def info(releaser):
    """Information of the application"""

    info = releaser.get_info()
    rolling = info["should_track_latest_release"] and "Yes" or "No"
    info_list = [
        f"App Name: {info['app_name']}",
        f"Device Type: {info['device_type']}",
        f"In Commit: {info['commit']}",
        f"Rolling enabled: {rolling}",
    ]
    click.echo("\n".join(info_list))


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
        commit = releases[0]["commit"]
        releaser.set_app_to_release(commit)
    click.echo("Enabled rolling")


@cli.command()
@pass_releaser
def show_devices_status(releaser):
    """Show the status of the devices in the applications"""

    devices = releaser.get_devices_by_status()
    for tag in devices:
        tag_devices = ", ".join([c["uuid"][:6] for c in devices[tag].values()])
        click.echo(f"{tag}: {tag_devices}")


@cli.command()
@click.argument("release_group")
@click.argument("release_commit")
@click.option("-y", is_flag=True)
@pass_releaser
@click.pass_context
def release(ctx, releaser, release_group, release_commit, y):
    """Sets release commits for a given release group"""
    if not releaser.is_valid_commit(release_commit):
        click.echo(f"Invalid release commit: {release_commit}")
        exit(2)
    if not releaser.is_valid_release_group(release_group):
        click.echo(f"Invalid release group: {release_group}")
        exit(3)

    ctx.invoke(info)
    click.echo("Devices:")
    ctx.invoke(show_devices_status)
    click.echo()

    confirm_text = f'Are you sure you want to set release group "{release_group}" to "{release_commit}"?'
    if not y and not click.confirm(confirm_text):
        click.echo("Cancelled!")
        exit(1)
    releaser.set_release(release_group, release_commit)


@cli.command()
@click.argument("release_group")
@pass_releaser
@click.pass_context
def unpin(ctx, releaser, release_group):
    """Unpins the version of a release group"""
    if not releaser.is_valid_release_group(release_group):
        click.echo(f"Invalid release group: {release_group}")
        exit(3)

    # Empty commit ID unpins devices
    releaser.set_release(release_group, "")


@cli.command()
@click.option("--count", default=10, help="How many")
@pass_releaser
def releases(releaser, count):
    """Show successful releases of the application"""
    releases = sorted(
        releaser.get_releases().values(),
        key=lambda rel: rel["end_timestamp"],
        reverse=True,
    )
    click.echo(f"Latest {count} releases:")
    for release in releases[:count]:
        click.echo(f'{release["end_timestamp"]} {release["commit"]}')


if __name__ == "__main__":
    cli()
