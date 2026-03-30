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
Unit tests for home_assistant Interface write path (switch / cover).

Uses **mock HTTP**: ``requests.post`` is patched so no real network traffic.
Assertions verify **URL** and **JSON payload** passed to ``requests.post``.

Run from ``services/core/PlatformDriverAgent`` (PYTHONPATH includes this dir), e.g.::

    set PYTHONPATH=.
    python -m pytest tests/test_home_assistant_unit.py --noconftest -v

``--noconftest`` avoids loading this package's conftest (Volttron platform fixtures),
so these tests run without a full platform / Linux-only imports.
"""

from unittest import mock

import pytest

from platform_driver.interfaces.home_assistant import HomeAssistantRegister, Interface

HA_BASE = "http://127.0.0.1:8123"


@pytest.fixture
def ha_iface():
    iface = Interface()
    iface.ip_address = "127.0.0.1"
    iface.port = 8123
    iface.access_token = "test-token"
    return iface


@pytest.fixture
def mock_http_post():
    """Patch module-level requests.post; return 200 so _post_method does not raise."""
    with mock.patch("platform_driver.interfaces.home_assistant.requests.post") as m:
        m.return_value = mock.MagicMock(status_code=200)
        yield m


def _assert_post_url_and_json(mock_post, expected_url, expected_json):
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == expected_url, f"URL: expected {expected_url!r}, got {args[0]!r}"
    assert kwargs.get("json") == expected_json, (
        f"json payload: expected {expected_json!r}, got {kwargs.get('json')!r}"
    )


def _reg_switch_state(point_name="switch_pt"):
    return HomeAssistantRegister(
        read_only=False,
        pointName=point_name,
        units="",
        reg_type=str,
        attributes={},
        entity_id="switch.test_unit",
        entity_point="state",
        default_value=None,
        description="",
    )


def _reg_cover_open_close(point_name="cover_oc"):
    return HomeAssistantRegister(
        read_only=False,
        pointName=point_name,
        units="",
        reg_type=str,
        attributes={},
        entity_id="cover.test_unit",
        entity_point="open/close",
        default_value=None,
        description="",
    )


def _reg_cover_position(point_name="cover_pos"):
    return HomeAssistantRegister(
        read_only=False,
        pointName=point_name,
        units="",
        reg_type=float,
        attributes={},
        entity_id="cover.test_unit",
        entity_point="position",
        default_value=None,
        description="",
    )


@pytest.mark.driver_unit
class TestHomeAssistantSwitchWrites:
    """Switch: true -> turn_on, false -> turn_off, invalid -> ValueError."""

    def test_switch_true_posts_turn_on_url_and_payload(self, ha_iface, mock_http_post):
        ha_iface.insert_register(_reg_switch_state())
        ha_iface._set_point("switch_pt", "true")
        _assert_post_url_and_json(
            mock_http_post,
            f"{HA_BASE}/api/services/switch/turn_on",
            {"entity_id": "switch.test_unit"},
        )

    def test_switch_false_posts_turn_off_url_and_payload(self, ha_iface, mock_http_post):
        ha_iface.insert_register(_reg_switch_state())
        ha_iface._set_point("switch_pt", "false")
        _assert_post_url_and_json(
            mock_http_post,
            f"{HA_BASE}/api/services/switch/turn_off",
            {"entity_id": "switch.test_unit"},
        )

    def test_switch_invalid_raises_valueerror_no_http(self, ha_iface, mock_http_post):
        ha_iface.insert_register(_reg_switch_state())
        with pytest.raises(ValueError):
            ha_iface._set_point("switch_pt", "invalid")
        mock_http_post.assert_not_called()


@pytest.mark.driver_unit
class TestHomeAssistantCoverWrites:
    """Cover: open/close/position services; invalid position -> ValueError."""

    def test_cover_open_posts_open_cover_url_and_payload(self, ha_iface, mock_http_post):
        ha_iface.insert_register(_reg_cover_open_close())
        ha_iface._set_point("cover_oc", "open")
        _assert_post_url_and_json(
            mock_http_post,
            f"{HA_BASE}/api/services/cover/open_cover",
            {"entity_id": "cover.test_unit"},
        )

    def test_cover_close_posts_close_cover_url_and_payload(self, ha_iface, mock_http_post):
        ha_iface.insert_register(_reg_cover_open_close())
        ha_iface._set_point("cover_oc", "close")
        _assert_post_url_and_json(
            mock_http_post,
            f"{HA_BASE}/api/services/cover/close_cover",
            {"entity_id": "cover.test_unit"},
        )

    def test_cover_position_50_posts_set_position_url_and_payload(self, ha_iface, mock_http_post):
        ha_iface.insert_register(_reg_cover_position())
        ha_iface._set_point("cover_pos", 50)
        _assert_post_url_and_json(
            mock_http_post,
            f"{HA_BASE}/api/services/cover/set_cover_position",
            {"entity_id": "cover.test_unit", "position": 50},
        )

    def test_cover_invalid_position_non_numeric_raises_no_http(self, ha_iface, mock_http_post):
        ha_iface.insert_register(_reg_cover_position())
        with pytest.raises(ValueError):
            ha_iface._set_point("cover_pos", "not_a_number")
        mock_http_post.assert_not_called()

    def test_cover_invalid_position_out_of_range_raises_no_http(self, ha_iface, mock_http_post):
        ha_iface.insert_register(_reg_cover_position())
        with pytest.raises(ValueError):
            ha_iface._set_point("cover_pos", 150)
        mock_http_post.assert_not_called()
