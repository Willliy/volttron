import pytest

from services.core.PlatformDriverAgent.platform_driver.interfaces.home_assistant import Interface


class DummyResponse:
    def __init__(self, status_code=200, text="", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


@pytest.fixture
def interface():
    test_interface = Interface()
    test_interface.configure(
        {
            "ip_address": "127.0.0.1",
            "access_token": "token",
            "port": "8123",
        },
        [
            {
                "Entity ID": "switch.demo_switch",
                "Entity Point": "state",
                "Volttron Point Name": "switch_state",
                "Units": "On / Off",
                "Writable": True,
                "Starting Value": False,
                "Type": "boolean",
            },
            {
                "Entity ID": "cover.demo_cover",
                "Entity Point": "open/close",
                "Volttron Point Name": "cover_state",
                "Units": "",
                "Writable": True,
                "Starting Value": "close",
                "Type": "string",
            },
            {
                "Entity ID": "cover.demo_cover",
                "Entity Point": "position",
                "Volttron Point Name": "cover_position",
                "Units": "%",
                "Writable": True,
                "Starting Value": 0,
                "Type": "float",
            },
        ]
    )
    return test_interface


@pytest.mark.parametrize(
    "value,expected_service",
    [
        (True, "turn_on"),
        (False, "turn_off"),
        ("on", "turn_on"),
        ("off", "turn_off"),
        ("true", "turn_on"),
        ("false", "turn_off"),
        (1, "turn_on"),
        (0, "turn_off"),
    ]
)
def test_switch_write_support_accepts_mvp_inputs(interface, monkeypatch, value, expected_service):
    captured = {}

    def fake_post(url, headers=None, json=None):
        captured["url"] = url
        captured["json"] = json
        return DummyResponse()

    monkeypatch.setattr(
        "services.core.PlatformDriverAgent.platform_driver.interfaces.home_assistant.requests.post",
        fake_post,
    )

    interface.set_point("switch_state", value)

    assert captured["url"].endswith(f"/api/services/switch/{expected_service}")
    assert captured["json"] == {"entity_id": "switch.demo_switch"}


def test_switch_write_support_rejects_invalid_inputs(interface):
    with pytest.raises(ValueError, match="true/1/on or false/0/off"):
        interface.set_point("switch_state", "maybe")


@pytest.mark.parametrize(
    "value,expected_service",
    [
        ("open", "open_cover"),
        ("close", "close_cover"),
    ]
)
def test_cover_open_close_uses_expected_services(interface, monkeypatch, value, expected_service):
    captured = {}

    def fake_post(url, headers=None, json=None):
        captured["url"] = url
        captured["json"] = json
        return DummyResponse()

    monkeypatch.setattr(
        "services.core.PlatformDriverAgent.platform_driver.interfaces.home_assistant.requests.post",
        fake_post,
    )

    interface.set_point("cover_state", value)

    assert captured["url"].endswith(f"/api/services/cover/{expected_service}")
    assert captured["json"] == {"entity_id": "cover.demo_cover"}


@pytest.mark.parametrize("value", [-1, 101, "abc"])
def test_cover_position_rejects_invalid_inputs(interface, value):
    with pytest.raises(ValueError, match="Position value for cover.demo_cover"):
        interface.set_point("cover_position", value)


def test_cover_position_sets_numeric_payload(interface, monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None):
        captured["url"] = url
        captured["json"] = json
        return DummyResponse()

    monkeypatch.setattr(
        "services.core.PlatformDriverAgent.platform_driver.interfaces.home_assistant.requests.post",
        fake_post,
    )

    interface.set_point("cover_position", "50.5")

    assert captured["url"].endswith("/api/services/cover/set_cover_position")
    assert captured["json"] == {"entity_id": "cover.demo_cover", "position": 50.5}


def test_parse_config_tracks_starting_values_for_revert(interface):
    assert interface._tracker.defaults["switch_state"] is False
    assert interface._tracker.defaults["cover_state"] == "close"
    assert interface._tracker.defaults["cover_position"] == 0
