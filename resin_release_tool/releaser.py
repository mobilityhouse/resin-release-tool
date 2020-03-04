from enum import Enum, unique
from functools import lru_cache
from balena import Balena
from balena.exceptions import BalenaException

@unique
class CliParamEnvModelMap(Enum):
    """Maps cli model name argument to model in balena sdk"""
    application = 'app'
    service_environment_variable = 'service'
    device = 'device'
    device_service_environment_variable = 'device_service'

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

    def is_device_level_environment_model(self, envar_model):
        envar_models = ['device', 'device_service_environment_variable']
        return self.get_envar_model_name(envar_model) in envar_models

    def is_application_level_environment_model(self, envar_model):
        envar_models = ['application', 'service_environment_variable']
        return self.get_envar_model_name(envar_model) in envar_models

    def validate_environment_model(self, envar_model):
        if not self.is_device_level_environment_model(envar_model) and \
               not self.is_application_level_environment_model(envar_model):
            raise ValueError(f'The environment {envar_model} model selected is invalid')

    def get_envar_model_name(self, envar_model):
        try:
            return CliParamEnvModelMap(envar_model).name
        except ValueError:
            raise ValueError(
                f'The environment {envar_model} model selected is invalid')

    def get_model_methods_base(self, envar_model):
        base_model_method = self.models.environment_variables
        model_method = getattr(
            base_model_method,
            f'{self.get_envar_model_name(envar_model)}')
        return model_method

    #To date, this doesnt filter by service name at any service level!
    def get_devices_filtered_by_condition(
            self, env_model, envar_name, envar_values, inclusive=False):
        if self.is_application_level_environment_model(env_model):
            devices = self._get_devices_by_envar_value_app_level(
                env_model, envar_name, envar_values, inclusive)
        elif self.is_device_level_environment_model(env_model):
            devices = self._get_devices_by_envar_value_device_level(
                env_model, envar_name, envar_values, inclusive)
        return devices

    def _get_devices_by_envar_value_app_level(
            self, env_model, envar_name, envar_values, inclusive=False):
        devices = ''
        envar_exists = False
        envars = self.get_envars_info_by_environment_model(
            env_model)
        if envar_name in envars.keys():
            if (envars[envar_name]['value'] in envar_values)\
                    == inclusive:
                devices = self.get_all_devices()
        if not envar_exists:
            raise ValueError(
                f'The variable {envar_name} does not exist in none of the devices.')
        if not devices:
            raise ValueError(
                f'No environment variable matchs the condition.')
        return devices

    def _get_devices_by_envar_value_device_level(
            self, env_model, envar_name, envar_values, inclusive=False):
        devices_filtered = []
        envar_exists = False
        devices = {d['id']:d for d in self.models.device.get_all()}
        for device in devices.values():
            device_envars = self.get_envars_info_by_environment_model(
                env_model, device)
            if envar_name in device_envars.keys():
                envar_exists = True
                device_envar_value = device_envars[envar_name]['value']
                if (device_envar_value in envar_values) == inclusive:
                    devices_filtered.append(device)
        if not envar_exists:
            raise ValueError(
                f'The variable {envar_name} does not exist in none of the devices.')
        if not devices_filtered:
            raise ValueError(
                f'No environment variable matchs the condition.')
        return {d['id']: d for d in devices_filtered}

    def get_envars_info_by_environment_model(self, envar_model, device=''):
        envar_model_name = self.get_envar_model_name(envar_model)
        model_methods = self.get_model_methods_base(envar_model)
        self.validate_environment_model(envar_model)
        if self.is_application_level_environment_model(envar_model):
            env_variables = model_methods.get_all(self.app_id)
        elif self.is_device_level_environment_model(envar_model) and device:
            env_variables = model_methods.get_all(device['uuid'])
        else:
            raise AttributeError(
                f'A device is needed for this environment model variables info.')
        return {env_variable['name']:env_variable \
                for env_variable in env_variables}

    def remove_from_environment_model_by_values(
            self, envar_model, envar_name, envar_values='', inclusive=False):
        self.validate_environment_model(envar_model)
        results = {}
        devices = self.get_devices_filtered_by_condition(
            envar_model, envar_name, envar_values, inclusive)
        if self.is_device_level_environment_model(envar_model):
            results = self._remove_envar_from_devices(
                envar_model, envar_name, devices)
        else:
            envars = self.get_envars_info_by_environment_model(
                envar_model)
            model_methods = self.get_model_methods_base(envar_model)
            try:
                model_methods.remove(envars[envar_name]['id'])
                results = 'Success!'
            except BalenaException as exception:
                results = f'Failed! {exception}'
        return results

    def _remove_envar_from_devices(self, envar_model, envar_name, devices):
        results = {'done':0, 'failed':0}
        for device in devices.values():
            envar_id = self.get_envars_info_by_environment_model(
                envar_model, device)[envar_name]['id']
            model_methods = self.get_model_methods_base(envar_model)
            try:
                model_methods.remove(envar_id)
                results['done'] += 1
            except BalenaException:
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
