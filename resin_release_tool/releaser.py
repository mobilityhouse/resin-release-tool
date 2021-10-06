from functools import lru_cache
from balena import Balena
from collections import defaultdict


class BalenaReleaser:
    def __init__(self, token, app_id):
        self.balena = Balena()
        self.balena.auth.login_with_token(token)

        self.models = self.balena.models

        self.app_id = app_id

    def get_info(self):
        return self.models.application.get_by_id(self.app_id)

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
        uuid_release_groups = defaultdict(list)
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
        # Disable rolling releases
        print("Disabling rolling releases on the application")
        self.disable_rolling()

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
            print(f"Setting app release to {release_hash}")
            self.set_app_to_release(release_hash)
