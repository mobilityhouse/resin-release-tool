from functools import lru_cache
from resin import Resin


class ResinReleaser:
    def __init__(self, token, app_id):
        self.resin = Resin()
        self.resin.auth.login_with_token(token)

        self.models = self.resin.models

        self.app_id = app_id

    def get_info(self):
        return self.models.application.get_by_id(self.app_id)

    def get_canaries(self):
        tags = self.models.tag.device.get_all_by_application(self.app_id)
        canaries = [
            tag['device']['__id'] for tag in tags
            if tag['tag_key'] == 'CANARY']
        return canaries

    @lru_cache()
    def get_releases(self):
        releases = self.models.release.get_all_by_application(self.app_id)
        return {
            release['commit']: release
            for release in releases
            if release['status'] == 'success'}

    def is_valid_commit(self, commit):
        return commit in self.get_releases()

    def disable_rolling(self):
        self.models.application.disable_rolling_updates(self.app_id)

    def enable_rolling(self):
        self.models.application.enable_rolling_updates(self.app_id)

    def set_app_to_release(self, release):
        self.models.application.set_to_release(self.app_id, release)

    def set_device_to_release(self, device, release):
        uuid = device['uuid']
        self.models.device.set_to_release(uuid, release)

    def get_all_devices(self):
        devices = self.models.device.get_all_by_application_id(self.app_id)
        return {d['id']: d for d in devices}

    @lru_cache()
    def get_devices_by_status(self):
        """Group devices by status: canary, old_canary, rest
        """
        all_devices = self.get_all_devices()
        canaries = {c: all_devices[c] for c in self.get_canaries()}

        def not_canary(device):
            return device['id'] not in canaries and \
                    device['should_be_running__release']

        old_canaries = {device['id']: device for device in all_devices.values()
                        if not_canary(device)}

        rest = {
          device['id']: device for device in all_devices.values()
          if device['id'] not in canaries and device['id'] not in old_canaries
        }

        return {
            'canaries': canaries,
            'old_canaries': old_canaries,
            'rest': rest,
        }

    def set_release(self, release_hash, canary_hash=None):
        devices = self.get_devices_by_status()

        canaries = devices['canaries']
        old_canaries = devices['old_canaries']

        # Disable rolling releases
        print('Disabling rolling releases on the application')
        self.disable_rolling()

        if old_canaries:
            print('Reseting all canaries')
            # Reset old canaries to app release
            for old_canary in old_canaries.values():
                print(old_canary['device_name'])
                self.set_device_to_release(old_canary, None)

        if canaries:
            print('Setting canaries')
            # Set canaries to current canary release
            for canary in canaries.values():
                print(canary['device_name'])
                self.set_device_to_release(canary, canary_hash)

        # We do this here to trigger update in all devices
        print('Setting up current release to: %s' % release_hash)
        self.set_app_to_release(release_hash)
