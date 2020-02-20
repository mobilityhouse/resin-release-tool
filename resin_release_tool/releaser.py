from functools import lru_cache
from balena import Balena


class BalenaReleaser:
    def __init__(self, token, app_id):
        self.balena = Balena()
        self.balena.auth.login_with_token(token)

        self.models = self.balena.models

        self.app_id = app_id

    def get_info(self):
        return self.models.application.get_by_id(self.app_id)

    def get_canaries(self):
        tags = self.models.tag.device.get_all_by_application(self.app_id)
        canaries = [
            tag['device']['__id'] for tag in tags
            if tag['tag_key'] == 'CANARY']
        return canaries

    def validate_environment_model(self, environment_model):
        if self.is_device_level_environment_model(environment_model) or \
                self.is_application_level_environment_model(environment_model):
            is_valid = True
        else: is_valid = False
        return is_valid

    def is_device_level_environment_model(self, environment_model):
        environment_models = ['devapp', 'devserv']
        return environment_model in environment_models

    def is_application_level_environment_model(self, environment_model):
        environment_models = ['app', 'serv']
        return environment_model in environment_models

    def get_devices_by_envar_name(self, envar, environment_model):
        if self.validate_environment_model(environment_model):
            if self.is_application_level_environment_model(environment_model):
                return self.get_all_devices()
            else:
                function = getattr(self, f'_get_devices_by_envar_name_{environment_model}')
        else:
            function = lambda _:\
                f'The environment {environment_model} model selected is invalid'
        return function(envar)

    def _get_devices_by_envar_name_devapp(self, envar):
        devices_filtered = []
        devices = self.models.device.get_all()
        for device in devices:
            device_env_variables = self._get_envars_info_devapp(device)
            if envar in device_env_variables.keys():
                devices_filtered.append(device)
        return {d['id']: d for d in devices_filtered}


#----------------------

    def get_envars_info(self, environment_model, *device):
        if self.validate_environment_model(environment_model):
            if self.is_device_level_environment_model(environment_model):
                function = getattr(self, f'_get_envars_info_{environment_model}')
                return function(device)

    def _get_envars_info_app(self):
        env_variables = self.models.environment_variables.\
            application.get_all(self.app_id)
        return self._formatted_envars_info(env_variables)

    def _get_envars_info_serv(self):
        pass

    def _get_envars_info_devapp(self, device):
        env_variables = self.models.\
            environment_variables.device.get_all(device['uuid'])
        return self._formatted_envars_info(env_variables)

    def _formatted_envars_info(self, env_variables):
        return {env_variable['name']:env_variable for \
                                env_variable in env_variables}

    def get_devices_filtered_by_envar_values(\
                                             self,\
                                             environment_model,\
                                             envar_name, envar_values,\
                                             inclusive_condition: bool = False):
        if self.is_device_level_environment_model(environment_model):
            devices_filtered = []
            devices = self.get_devices_by_envar_name(envar_name, environment_model)
            for device in devices.values():
                device_envar_value = self.\
                    get_envars_info(environment_model, device)[envar_name]['value']
                if (device_envar_value in envar_values) == inclusive_condition:
                    devices_filtered.append(device)
            return {d['id']: d for d in devices_filtered}
        else:
            return 'The environment model is not valid on this method.'

    def remove_envar_of_environment_model(self, envar_name, \
                                            environment_model, *devices):
        if self.validate_environment_model(environment_model):
            if self.is_device_level_environment_model(environment_model):
                if not devices:
                    return 'There are no devices to remove environment variable.'
            function = getattr(self, f'_remove_envar_of_{environment_model}')
            return function(envar_name)

    def _remove_envar_of_devserv(self, envar_name, devices):
        results = {'done':0, 'failed':0}
        for device in devices:
            envar_id = self._get_envars_info_devapp(device)[envar_name]['id']
            try:
                self.models.environment_variables.device.remove(envar_id)
                results['done'] += 1
            except:
                results['failed'] += 1
                results['failed_devices'][device['uuid']] = device
        return results

    def _remove_envar_of_devapp(self, envar_name, devices):
        results = {'done':0, 'failed':0}
        for device in devices:
            envar_id = self._get_envars_info_devapp(device)[envar_name]['id']
            try:
                self.models.environment_variables.device.remove(envar_id)
                results['done'] += 1
            except:
                results['failed'] += 1
                results['failed_devices'][device['uuid']] = device
        return results

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
