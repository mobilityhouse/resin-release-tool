from unittest.mock import MagicMock, Mock

from resin_release_tool.releaser import BalenaReleaser
from resin_release_tool.balena_backend import BalenaBackend
import pytest


@pytest.fixture()
def balena_sdk_get_application_info():
    return {
        "app_name": "my_fleet",
        "is_for__device_type": {
            # '__deferred': {'uri': '/resin/device_type(@id)?@id=58'},
            "__id": 58
        },
        "should_be_running__release": {
            # '__deferred': {'uri': '/resin/release(@id)?@id=2073634'},
            "__id": 2073634
        },
        "should_track_latest_release": False,
    }


@pytest.fixture()
def balena_sdk_device_type():
    return {
        "name": "Raspberry Pi 3",
    }


@pytest.fixture()
def balena_release():
    return {
        "commit": "2727adf02f82035cd32b26749db274f5",
    }


def make_device(**kwargs):
    """fixture factory for mocking a device
    for current tests we only need the fields below and we can add more as needed
    """
    device_data = {"id": 5883496, "is_running__release": {"__id": 1234}}
    device_data.update(kwargs)
    return device_data


@pytest.fixture
def mock_balena_backend(
    balena_sdk_get_application_info, balena_sdk_device_type, balena_release
):
    mock = MagicMock(BalenaBackend)
    mock.get_application_info.return_value = balena_sdk_get_application_info
    mock.get_device_type_by_id.return_value = balena_sdk_device_type
    mock.get_release_by_id.return_value = balena_release
    return mock


def test_get_info_for_rolling_relase(
    mock_balena_backend, balena_sdk_get_application_info
):
    balena_sdk_get_application_info["should_track_latest_release"] = True
    mock_balena_backend.get_application_info.return_value = (
        balena_sdk_get_application_info
    )
    releaser = BalenaReleaser(
        token="fake_token", app_id="123", balena_backend=mock_balena_backend
    )

    assert "Rolling enabled: Yes" in releaser.get_info()


def test_get_commit_info(mock_balena_backend):
    releaser = BalenaReleaser(
        token="fake_token", app_id="123", balena_backend=mock_balena_backend
    )

    assert "In Commit: 2727adf02f82035cd32b26749db274f5" in releaser.get_info()


def test_get_info(mock_balena_backend):
    releaser = BalenaReleaser(
        token="fake_token", app_id="123", balena_backend=mock_balena_backend
    )
    assert releaser.get_info() == [
        "Fleet Name: my_fleet",
        "Device Type: Raspberry Pi 3",
        "In Commit: 2727adf02f82035cd32b26749db274f5",
        "Rolling enabled: No",
    ]


@pytest.fixture
def echo():
    """test double for asserting on the lines that would get send to click.echo"""

    class _echo:
        lines = []

        def __call__(self, line):
            self.lines.append(line)

    return _echo()


def test_show_group_versions(mock_balena_backend, echo):
    releaser = BalenaReleaser(
        token="fake_token", app_id="123", balena_backend=mock_balena_backend
    )
    mock = Mock()
    mock.return_value = {
        None: {123: make_device(id=123)},
        "group_two": {124: make_device(id=124)},
    }
    releaser.get_devices_by_status = mock

    releaser.show_group_versions(output=echo)

    assert echo.lines == ["None: 2727adf", "group_two: 2727adf"]


def test_check_sdk_version(echo):
    releaser = BalenaReleaser(
        token="fake_token",
        app_id="123",
        balena_backend=mock_balena_backend,
        output=echo,
    )

    releaser.balena.settings = {"api_version": BalenaBackend.SUPPORTED_API_VERSION}
    releaser._check_sdk_version()

    assert echo.lines == []


def test_check_sdk_version_should_warn_for_outdated_api_in_balena_settings_config(echo):
    releaser = BalenaReleaser(
        token="fake_token",
        app_id="123",
        balena_backend=mock_balena_backend,
        output=echo,
    )

    releaser.balena.settings = {"api_version": "v5"}

    releaser._check_sdk_version()

    assert (
        "Warning: Your configured api version in $HOME/.balena/balena.cfg is: 'v5'"
        in ("").join(echo.lines).replace("\n", " ")
    )
    assert "balena sdk default is: 'v6'" in ("").join(echo.lines).replace("\n", " ")
    assert "supported version is: 'v6'" in ("").join(echo.lines).replace("\n", " ")
