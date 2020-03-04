import click
from .releaser import BalenaReleaser


# get releaser object from the context
pass_releaser = click.make_pass_decorator(BalenaReleaser)


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
    ctx.obj = BalenaReleaser(token, app)


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
    releases = sorted(releaser.get_releases().values(),
                      key=lambda rel: rel['end_timestamp'],
                      reverse=True)
    click.echo(f'Latest {count} releases:')
    for release in releases[:count]:
        click.echo(f'{release["end_timestamp"]} {release["commit"]}')


@cli.command()
@pass_releaser
def show_devices(releaser, devices_to_show):
    devices_to_show= ', '.join(
        [c['uuid'][:6] for c in devices_to_show.values()])
    click.echo(f'uuids: {devices_to_show}')


@cli.command()
@click.argument('filtering_params')
@click.argument('envar_value')
@click.option('--inclusive', is_flag=True, default=True, help=\
              'Defines if filtering must be inclusive or not for the envar_value values')
@pass_releaser
@click.pass_context
def filter_and_remove_env_var(ctx, releaser, filtering_params,\
                              envar_value, inclusive):
    """
    Filter devices by enviroment variables and removes them.

    -filtering_params: 'envar_model:envar_name' in not service
    nor device_service envar_model and 'envar_model:service_name:envar_name'
    for service envar filtering.


    envar_model:

        >   Application: app

        >   Service: service

        >   Device Application: devices

        >   Device Service: device_service

    service_name:
    Only required when envar_model is service or device_service. Is the name
    of the service that contains the requested envar.
)
    envar_name:
    Name of the environment variable to remove.

    -envar_value:
    Posible values to use to filter. Could be a list or empty.
    """

    processed_filtering_params = filtering_params.split(':')
    if len(processed_filtering_params) == 3:
        envar_model, service_name, envar_name = processed_filtering_params
    elif len(processed_filtering_params) == 2:
        envar_model, envar_name = processed_filtering_params
        service_name = ''
    else:
        raise ValueError(f'The parameters for filtering are not correct')

    try:
        devices = (device['device'] for device \
                   in releaser.get_devices_and_envar_id_filtered_by_condition(
                       envar_model, envar_name, envar_value, service_name,\
                       inclusive))
    except ValueError as exception:
        click.echo(exception)
        exit(2)
    ctx.invoke(info)
    click.echo('Devices to be modified:')

    list_devices = list(devices)
    list_devices_len = len(list_devices)
    list_devices_info = ', '.join([uuid[:6] for uuid in list_devices[:10]])
    if list_devices_len > 10:
        list_devices_info += f'... and {list_devices_len-10} more'
    click.echo(f'uuids: {list_devices_info}')

    confirm_text = 'Are you sure you want to delete '\
        'the environment variable "%s" for this devices?' % (
            envar_name)
    if not click.confirm(confirm_text):
        click.echo('Cancelled!')
        exit(1)
    results = releaser.remove_from_environment_model_by_values(
        envar_model, envar_name, envar_value, service_name, inclusive)
    click.echo(results)

if __name__ == '__main__':
    cli()
