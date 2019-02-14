from functools import lru_cache
from resin import Resin
import json


class ResinReleaser:
    def __init__(self, token, app_id):
        self.resin = Resin()
        self.resin.auth.login_with_token(token)

        self.models = self.resin.models

        self.app_id = app_id

        self.uuid_list = [] #list of all the UUIDs in the app
        
    def get_info(self):
        return self.models.application.get_by_id(self.app_id)

    def get_canaries(self):
        tags = self.models.tag.device.get_all_by_application(self.app_id)
        canaries = [
            tag['device']['__id'] for tag in tags
            if tag['tag_key'] == 'CANARY']
        return canaries

    def get_tags_per_device(self):
        all_devices = self.get_all_devices()
        tags = self.models.tag.device.get_all_by_application(self.app_id)
        device_dict = {}
        for device in all_devices.values():
            device_id = device['id']
            device_dict[device_id] = {
                'uuid': device['uuid'],
                'tags': {},
            }
        for elem in tags:
            device_id = elem['device']['__id']
            tag_key = elem['tag_key']
            value = elem['value']
            device_dict[device_id]['tags'][tag_key] = value
        tags_per_device = [device_dict[device] for device in list(device_dict.keys())]
        return tags_per_device
                    
    def get_app_env_vars(self):        
        allvars = self.models.environment_variables.application.get_all(int(self.app_id))
        list_of_app_env_vars = [{'id':var['id'], var['name']:var['value']} for var in allvars]
        return list_of_app_env_vars
        
    def get_device_env_vars(self):
        list_of_env_vars_per_device = []
        for device in self.uuid_list:
            allvars = self.models.environment_variables.device.get_all(device)
            list_of_vars = [{'id':var['id'], var['name']:var['value']} for var in allvars]
            list_of_env_vars_per_device.append({device:list_of_vars})
        return list_of_env_vars_per_device

    def set_device_env_vars_from_tags(self, tags_per_device, device_env_vars):
        for device in tags_per_device:
            uuid = device['uuid']
            print("----------------------------------------------------------")
            print("Device: ", uuid)
            try:
                value = json.dumps(device['tags'])
                self.models.environment_variables.device.create(device['uuid'], 'DEVICE_TAG_LIST', value)
                print("creating/overriding var: ", device['uuid'], 'DEVICE_TAG_LIST', value)
            except:
                print("env var 'DEVICE_TAG_LIST' already exists!")
                for elem in device_env_vars:
                    if uuid in elem:
                        list_of_env_vars = elem[uuid]
                        for var in list_of_env_vars:
                            if 'DEVICE_TAG_LIST' in var:
                                var_id = var['id']
                                old_val = var['DEVICE_TAG_LIST']
                                if old_val != value:
                                    print("Updating var DEVICE_TAG_LIST with value", value)
                                    self.models.environment_variables.device.update(var_id, value)
                                else:
                                    print("Not updating var DEVICE_TAG_LIST since the value did not change!")
    
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
