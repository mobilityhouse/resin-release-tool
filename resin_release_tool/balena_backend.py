from typing import Dict
from balena import exceptions


class BalenaBackend:
    """Wrapper around the balena_sdk to make it easier to swap it out for unit testing.

    The SUPPORTED_API_VERSION is used to pin the expected Balena Api version used by the balena-sdk installation.
    It is used to show a warning if the Api version changes, as this might introduce breaking changes.
    """

    SUPPORTED_API_VERSION = "v6"

    def __init__(self, models, settings):
        self.models = models
        self.settings = settings

    def get_application_info(self, id: int) -> Dict:
        """https://www.balena.io/docs/reference/sdk/python-sdk/#function-get_by_idapp_id
        note that the Example response documented there differs from the actual response
        (which is missing device_type and commit)
        """
        return self.models.application.get_by_id(id)

    def _get_application_base_request(self):
        return self.models.application.base_request

    def get_release_by_id(self, id: int) -> Dict:
        return self._get_resource_by_id("release", id)

    def get_device_type_by_id(self, id: int) -> Dict:
        return self._get_resource_by_id("device_type", id)

    def _get_resource_by_id(self, resource: str, id: int) -> Dict:
        base_request = self._get_application_base_request()
        params = {"filters": {"id": id}}
        response = base_request.request(
            resource, "GET", params=params, endpoint=self.settings.get("pine_endpoint")
        )
        if response["d"]:
            assert (
                len(response["d"]) == 1
            ), f"getting device type by id should return one type {response['d']}"
            return response["d"][0]
        else:
            raise ResourceNotFound(f"{resource} {params}")


class ResourceNotFound(exceptions.BalenaException):
    def __init__(self, message):
        super(ResourceNotFound, self).__init__()
        self.message = "Resource not found: {message}".format(message=message)
