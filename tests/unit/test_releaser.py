from unittest.mock import MagicMock
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
