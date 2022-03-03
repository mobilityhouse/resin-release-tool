import click
from resin_release_tool.releaser import BalenaReleaser

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
    click.echo("\n".join(releaser.get_info()))


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
    releases = list(releaser.get_releases().values())
    if releases:
        commit = releases[-1]["commit"]
        releaser.set_app_to_release(commit)
    releaser.enable_rolling()
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
@pass_releaser
def show_group_versions(releaser):
    """Show the release versions of the devices in release groups"""
    releaser.show_group_versions()


@cli.command()
@click.option("--group", "-g", help="Name of release group (needed if -a is not used)")
@click.option("--commit", "-c", required=True)
@click.option(
    "--app",
    "-a",
    is_flag=True,
    help="Flag to set the app-wide release (needed if -g is not used)",
)
@click.option("--yes", "-y", is_flag=True, help="Don't ask for confirmation")
@click.option(
    "--silent", is_flag=True, help="Don't show info or status before setting release"
)
@pass_releaser
@click.pass_context
def release(ctx, releaser, group, commit, app, yes, silent):
    """Sets release commits for a given release group or app"""
    if not group and not app:
        click.echo('Error: Missing option "--group" / "-g" or flag "--app" / "-a".')
        exit(4)

    if not releaser.is_valid_commit(commit):
        click.echo(f"Invalid release commit: {commit}")
        exit(2)
    if group and not releaser.is_valid_release_group(group):
        click.echo(f"Invalid release group: {group}")
        exit(3)

    if not silent:
        ctx.invoke(info)
        click.echo("Devices:")
        ctx.invoke(show_devices_status)
        click.echo()

    # TODO: this doesn't account for both -a and -g being set
    group_name = f'release group "{group}"' if group else "app"

    confirm_text = f'Are you sure you want to set {group_name} to "{commit}"?'
    if not yes and not click.confirm(confirm_text):
        click.echo("Cancelled!")
        exit(1)
    releaser.set_release(commit, group, app)


@cli.command()
@click.argument("release_group", nargs=-1)
@click.option("--nocheck", is_flag=True, help="Don't check if the release group exists")
@pass_releaser
@click.pass_context
def unpin(ctx, releaser, release_group, nocheck):
    """Unpins the version of one or more release groups"""
    # Doing for loops separately so an exit doesn't happen midway
    for group in release_group:
        if not nocheck and not releaser.is_valid_release_group(group):
            click.echo(f"Invalid release group: {group}")
            exit(3)

    for group in release_group:
        # Empty commit ID unpins devices
        releaser.set_release(None, group)


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
