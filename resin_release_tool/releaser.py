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
            self.get_envar_model_name(envar_model))
        return model_method

    def get_devices_and_envar_id_filtered_by_condition(
            self, env_model, envar_name, envar_values, \
            service_name='', inclusive=True):

        if self.is_application_level_environment_model(env_model):
            devices_with_envar_id = self._get_devices_and_envar_id_by_envar_value_app_level(
                env_model, envar_name, envar_values, service_name, inclusive)

        elif self.is_device_level_environment_model(env_model):
            devices_with_envar_id = self._get_devices_and_envar_id_by_envar_value_device_level(
                env_model, envar_name, envar_values, service_name, inclusive)
        return devices_with_envar_id

    def _get_devices_and_envar_id_by_envar_value_app_level(
            self, env_model, envar_name, envar_values,\
            service_name='', inclusive=True):
        devices = {}
        envars_by_model = self.get_envars_info_by_environment_model(env_model)
        envars = {envar['id']:{
            'name':envar['name'],
            'value':envar['value'],
        } for envar in envars_by_model.values()}

        envar_names = [envar['name'] for envar in envars.values()]

        if not envar_name in envar_names:
            raise ValueError(
                f'The variable {envar_name} does not exist in none of the devices.')

        if self.get_envar_model_name(env_model) ==\
                'service_environment_variable':

            if not service_name:
                raise ValueError(
                    f'Service name parameter is required for this operation.')
            services = {s['id']:s for s in self.models.service.\
                        get_all_by_application(self.app_id)}
            envar_on_service = False

            for envar in envars:
                envars_service_id = envars_by_model[envar]['service']['__id']
                if services[envars_service_id]['service_name'] == service_name:
                    envars = {envar:envars[envar]}
                    envar_on_service = True
                    break
            if not envar_on_service:
                raise ValueError(
                    f'The environment variable does not exists on this service')

        for envar in envars:
            if envars[envar]['name'] == envar_name and\
                    (envars[envar]['value'] in envar_values) == inclusive:
                devices = [device['uuid'] for device in self.\
                           get_all_devices().values()]

        if not devices:
            raise ValueError(
                f'No environment variable matchs the condition.')
        return {'devices': devices, 'envar_id': envar}

    def _get_devices_and_envar_id_by_envar_value_device_level(
            self, env_model, envar_name, envar_values,\
            service_name='', inclusive=True):
        devices_filtered = []
        envar_exists = False
        envar_on_service = False
        devices = {d['id']:d for d in self.models.device.get_all()}

        for device in devices.values():
            envars_by_model = self.get_envars_info_by_environment_model(
                env_model, device)
            envars = {envar['id']:{
                'name':envar['name'],
                'value':envar['value'],
            } for envar in envars_by_model.values()}
            envar_names = [envar['name'] for envar in envars.values()]
            if envar_name in envar_names:
                envar_exists = True

            #If is device service environment, the filtering is different.
            if self.get_envar_model_name(env_model) ==\
                    'device_service_environment_variable':

                if not service_name:
                    raise ValueError(
                        f'Service name parameter is required for this operation')

                for envar in envars:
                    envar_service_name = envars_by_model[envar]\
                        ['service_install'].pop()\
                        ['service'].pop()\
                        ['service_name']

                    if envar_service_name == service_name:
                        envars = {envar:envars[envar]}
                        envar_on_service = True
                        break

            for envar in envars:
                if envars[envar]['name'] == envar_name and\
                        (envars[envar]['value'] in envar_values) == inclusive:
                    devices_filtered.append({
                        'device': device['uuid'],
                        'envar_id': envar,
                    })

        if not envar_exists:
            raise ValueError(
                f'The variable {envar_name} does not exist in none of the devices.')

        if self.get_envar_model_name(env_model) == \
                'device_service_environment_variable' and \
                not envar_on_service:
            raise ValueError(
                f'The environment variable does not exists on this service')

        if not devices_filtered:
            raise ValueError(
                f'No environment variable matchs the condition.')


        return devices_filtered

    def get_envars_info_by_environment_model(self, envar_model, device=''):
        envar_model_name = self.get_envar_model_name(envar_model)
        model_methods = self.get_model_methods_base(envar_model)
        self.validate_environment_model(envar_model)

        if self.is_application_level_environment_model(envar_model):
            if self.get_envar_model_name(envar_model) ==\
                    'service_environment_variable':
                env_variables = model_methods.get_all_by_application(self.app_id)
            else: env_variables = model_methods.get_all(self.app_id)

        elif self.is_device_level_environment_model(envar_model) and device:
            env_variables = model_methods.get_all(device['uuid'])

        else:
            raise AttributeError(
                f'A device is needed for this environment model variables info.')

        return {env_variable['id']:env_variable \
                for env_variable in env_variables}

    def remove_from_environment_model_by_values(
            self, envar_model, envar_name, envar_values='',
            service_name='', inclusive=True):
        self.validate_environment_model(envar_model)
        results = {}
        devices_with_envar_id = self.get_devices_and_envar_id_filtered_by_condition(
            envar_model, envar_name, envar_values, service_name, inclusive)

        if self.is_device_level_environment_model(envar_model):
            results = self._remove_envar_from_devices(envar_model, devices_with_envar_id)
        else:
            model_methods = self.get_model_methods_base(envar_model)
            try:
                model_methods.remove(devices_with_envar_id['envar_id'])
                results = 'Success!'
            except BalenaException as exception:
                results = f'Failed! {exception}'
        return results

    def _remove_envar_from_devices(self, envar_model, devices_with_envar_id):
        results = {'Done':0, 'Failed':0}

        for device in devices_with_envar_id:
            model_methods = self.get_model_methods_base(envar_model)
            try:
                model_methods.remove(device['envar_id'])
                results['Done'] += 1
            except BalenaException:
                results['Failed'] += 1
                results['Failed_Devices'] = device['uuid']
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
