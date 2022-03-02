from functools import lru_cache
from typing import Callable

import click
from balena import Balena, Settings
from resin_release_tool.balena_backend import BalenaBackend
from collections import defaultdict


class BalenaReleaser:
    def __init__(
        self, token, app_id, balena_backend=None, output: Callable = click.echo
    ):
        self.balena = Balena()
        self.balena.auth.login_with_token(token)

        # deprecated way to access the models
        # for new functionality use balena_backend.models as this makes testing easier
        self.models = self.balena.models

        if balena_backend is None:
            balena_backend = BalenaBackend(
                models=self.models, settings=self.balena.settings
            )
        self.balena_backend = balena_backend
        self.echo = output
        self.app_id = app_id

        self._check_sdk_version()

    def _check_sdk_version(self):
        """The Balena sdk creates on installation a config file which sets the version to use for this user"""
        try:
            configured_version = self.balena.settings.get("api_version")
            default_version = Settings._setting.get("api_version")
            if (
                configured_version != BalenaBackend.SUPPORTED_API_VERSION
                or default_version != BalenaBackend.SUPPORTED_API_VERSION
            ):
                msg = f"Warning: \
Your configured api version in $HOME/.balena/balena.cfg is: '{configured_version}' \
The balena sdk default is: '{default_version}'. The supported version is: '{BalenaBackend.SUPPORTED_API_VERSION}'.  \
Check also 'pine_endpoint' there\n"
                self._print_notice(msg)
        except Exception as e:
            self._print_notice(f"\nERROR check settings versions: {e}\n")

    def _print_notice(self, message):
        self.echo(
            click.wrap_text(
                "****************************\n"
                + message
                + "****************************\n"
            )
        )

    def get_info(self):
        fleet_info = self.balena_backend.get_application_info(self.app_id)
        device_type = self.balena_backend.get_device_type_by_id(
            fleet_info.get("is_for__device_type").get("__id")
        )
        release = self.balena_backend.get_release_by_id(
            fleet_info.get("should_be_running__release").get("__id")
        )
        rolling = fleet_info["should_track_latest_release"] and "Yes" or "No"
        info_list = [
            f"Fleet Name: {fleet_info['app_name']}",
            f"Device Type: {device_type.get('name')}",
            f"In Commit: {release.get('commit')}",
            f"Rolling enabled: {rolling}",
        ]
        return info_list

    def get_release_group(self, release_group):
        tags = self.models.tag.device.get_all_by_application(self.app_id)
        release_group_devices = [
            tag["device"]["__id"]
            for tag in tags
            if tag["tag_key"] == "release_group" and tag["value"] == release_group
        ]
        return release_group_devices

    @lru_cache()
    def get_releases(self):
        releases = self.models.release.get_all_by_application(self.app_id)
        return {
            release["commit"]: release
            for release in releases
            if release["status"] == "success"
        }

    @lru_cache()
    def get_release_groups(self):
        tags = self.models.tag.device.get_all_by_application(self.app_id)

        release_groups = defaultdict(list)
        for tag in tags:
            if tag["tag_key"] != "release_group":
                continue
            release_groups[tag["value"]].append(tag["device"]["__id"])

        return dict(release_groups)

    def is_valid_commit(self, commit):
        return commit in self.get_releases()

    def is_valid_release_group(self, release_group):
        return release_group in self.get_release_groups()

    def disable_rolling(self):
        self.models.application.disable_rolling_updates(self.app_id)

    def enable_rolling(self):
        self.models.application.enable_rolling_updates(self.app_id)

    def set_app_to_release(self, release):
        self.models.application.set_to_release(self.app_id, release)

    def set_device_to_release(self, device, release):
        uuid = device["uuid"]
        self.models.device.set_to_release(uuid, release)

    def get_all_devices(self):
        devices = self.models.device.get_all_by_application_id(self.app_id)
        return {d["id"]: d for d in devices}

    @lru_cache()
    def get_devices_by_status(self):
        """Group devices by their release groups.
        Devices without one will be under key None."""
        all_devices = self.get_all_devices()
        release_groups = self.get_release_groups()
        uuid_release_groups = {}
        for device_group in release_groups:
            uuid_release_groups[device_group] = {
                device: all_devices[device] for device in release_groups[device_group]
            }

        uuid_release_groups[None] = {
            device["id"]: device
            for device in all_devices.values()
            if device["id"] not in sum(release_groups.values(), [])
        }

        return dict(uuid_release_groups)

    def set_release(self, release_hash, release_group, app_wide=False):
        # TODO: This is a bit overly nested.
        if release_group:
            devices = self.get_devices_by_status()
            release_group_devices = devices[release_group]

            if release_group_devices:
                print(f"Setting {release_group} release group to {release_hash}")
                # Set canaries to current canary release
                for device in release_group_devices.values():
                    print(device["device_name"])
                    self.set_device_to_release(device, release_hash)

        if app_wide:
            # Disable rolling releases
            print("Disabling rolling releases on the application")
            self.disable_rolling()

            print(f"Setting app release to {release_hash}")
            self.set_app_to_release(release_hash)

    def show_group_versions(self, output: Callable = click.echo):
        devices = self.get_devices_by_status()
        for tag in devices:
            release_ids = [
                c["is_running__release"]["__id"] for c in devices[tag].values()
            ]

            release_versions = [
                self.balena_backend.get_release_by_id(_id)["commit"][:7]
                for _id in release_ids
            ]
            if not release_versions:
                continue

            tag_devices = ", ".join(set(release_versions))
            output(f"{tag}: {tag_devices}")
