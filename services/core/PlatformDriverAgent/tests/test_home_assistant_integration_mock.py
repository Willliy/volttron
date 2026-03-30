# -*- coding: utf-8 -*- {{{
# ===----------------------------------------------------------------------===
#
#                 Component of Eclipse VOLTTRON
#
# ===----------------------------------------------------------------------===
#
# Copyright 2023 Battelle Memorial Institute
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# ===----------------------------------------------------------------------===
# }}}

"""
Mock **integration** tests: **driver → HTTP API → response handling**.

Uses real :class:`platform_driver.driver.DriverAgent` with ``setup_device()`` so the
home_assistant interface is loaded as in production, then calls ``set_point`` /
``get_point``. All HTTP is mocked (no real Home Assistant).

**PYTHONPATH** must include the **Volttron repo root** and **PlatformDriverAgent**::

    # PowerShell example (adjust path)
    $root = "C:\\...\\volttron"
    $pda = "$root\\services\\core\\PlatformDriverAgent"
    $env:PYTHONPATH = "$root;$pda"
    python -m pytest tests/test_home_assistant_integration_mock.py --noconftest -v

If ``volttron`` is not importable, collection skips this module.
"""

from unittest import mock

import pytest

pytest.importorskip("volttron.platform.vip.agent")

from platform_driver.driver import DriverAgent

HA_BASE = "http://127.0.0.1:8123"


def _ha_registry_switch():
    return [
        {
            "Entity ID": "switch.test_unit",
            "Entity Point": "state",
            "Volttron Point Name": "switch_pt",
            "Units": "",
            "Writable": True,
            "Starting Value": 0,
            "Type": "string",
        }
    ]


def _ha_registry_cover():
    return [
        {
            "Entity ID": "cover.test_unit",
            "Entity Point": "open/close",
            "Volttron Point Name": "cover_oc",
            "Units": "",
            "Writable": True,
            "Starting Value": "close",
            "Type": "string",
        }
    ]


def _ha_registry_read_state():
    """Point name matches HA ``state`` field for :meth:`Interface.get_point` lookup."""
    return [
        {
            "Entity ID": "switch.test_unit",
            "Entity Point": "state",
            "Volttron Point Name": "state",
            "Units": "",
            "Writable": False,
            "Starting Value": 0,
            "Type": "string",
        }
    ]


def _make_home_assistant_driver(registry_rows, device_path="devices/ha_integration_mock"):
    parent = mock.MagicMock()
    parent.vip = mock.MagicMock()
    config = {
        "driver_type": "home_assistant",
        "driver_config": {
            "ip_address": "127.0.0.1",
            "access_token": "integration-test-token",
            "port": 8123,
        },
        "registry_config": registry_rows,
        "interval": 60,
        "timezone": "UTC",
    }
    agent = DriverAgent(parent, config, 0, 1, device_path, 0, 0)
    agent.setup_device()
    return agent


def _assert_post_url_and_json(mock_post, expected_url, expected_json):
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == expected_url
    assert kwargs.get("json") == expected_json


@pytest.mark.driver_unit
class TestHomeAssistantDriverIntegrationMockPost:
    """DriverAgent.set_point → interface → requests.post (mocked)."""

    def test_driver_switch_true_posts_turn_on(self):
        agent = _make_home_assistant_driver(_ha_registry_switch())
        with mock.patch("platform_driver.interfaces.home_assistant.requests.post") as post:
            post.return_value = mock.MagicMock(status_code=200)
            result = agent.set_point("switch_pt", "true")
        _assert_post_url_and_json(
            post,
            f"{HA_BASE}/api/services/switch/turn_on",
            {"entity_id": "switch.test_unit"},
        )
        assert result is not None

    def test_driver_cover_open_posts_open_cover(self):
        agent = _make_home_assistant_driver(_ha_registry_cover())
        with mock.patch("platform_driver.interfaces.home_assistant.requests.post") as post:
            post.return_value = mock.MagicMock(status_code=200)
            result = agent.set_point("cover_oc", "open")
        _assert_post_url_and_json(
            post,
            f"{HA_BASE}/api/services/cover/open_cover",
            {"entity_id": "cover.test_unit"},
        )
        assert result is not None


@pytest.mark.driver_unit
class TestHomeAssistantDriverIntegrationMockResponseHandling:
    """Non-2xx HTTP responses surface as errors after driver set_point."""

    def test_driver_set_point_raises_on_api_error_status(self):
        agent = _make_home_assistant_driver(_ha_registry_switch())
        with mock.patch("platform_driver.interfaces.home_assistant.requests.post") as post:
            post.return_value = mock.MagicMock(status_code=400, text="Bad Request")
            with pytest.raises(Exception):
                agent.set_point("switch_pt", "true")


@pytest.mark.driver_unit
class TestHomeAssistantDriverIntegrationMockGet:
    """DriverAgent.get_point → interface → requests.get (mocked) → parsed body."""

    def test_driver_get_point_uses_get_url_and_returns_state(self):
        agent = _make_home_assistant_driver(_ha_registry_read_state())
        fake_body = {"state": "on", "attributes": {}}
        with mock.patch("platform_driver.interfaces.home_assistant.requests.get") as get:
            get.return_value = mock.MagicMock(status_code=200)
            get.return_value.json.return_value = fake_body
            value = agent.get_point("state")
        get.assert_called_once()
        args, kwargs = get.call_args
        assert args[0] == f"{HA_BASE}/api/states/switch.test_unit"
        assert value == "on"
