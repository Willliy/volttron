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


from platform_driver.interfaces import BaseInterface, BaseRegister, BasicRevert
import logging
import requests
_log = logging.getLogger(__name__)
type_mapping = {"string": str,
                "int": int,
                "integer": int,
                "float": float,
                "bool": bool,
                "boolean": bool}
_CLIMATE_HA_STATE_TO_VOLTTRON = {"off": 0, "heat": 2, "cool": 3, "auto": 4}
_CLIMATE_VOLTTRON_TO_HVAC_MODE = {0: "off", 2: "heat", 3: "cool", 4: "auto"}
class HomeAssistantRegister(BaseRegister):
    def __init__(self, read_only, pointName, units, reg_type, attributes, entity_id, entity_point, default_value=None,
                 description=''):
        super(HomeAssistantRegister, self).__init__("byte", read_only, pointName, units, description='')
        self.reg_type = reg_type
        self.attributes = attributes
        self.entity_id = entity_id
        self.value = None
        self.entity_point = entity_point


def _post_method(url, headers, data, operation_description):
    err = None
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            _log.info(f"Success: {operation_description}")
        else:
            err = (f"Failed to {operation_description}. Status code: {response.status_code}. "
                   f"Response: {response.text}")
    except requests.RequestException as e:
        err = f"Error when attempting - {operation_description} : {e}"
    if err:
        _log.error(err)
        raise Exception(err)


def parse_domain(entity_id):
    """Return Home Assistant domain from entity_id (e.g. 'light.kitchen' -> 'light')."""
    if not entity_id or "." not in entity_id:
        return ""
    return entity_id.split(".", 1)[0]


class WriteStrategy:
    def execute(self, interface, register, point_name):
        raise NotImplementedError


class LightWriteStrategy(WriteStrategy):
    def execute(self, interface, register, point_name):
        entity_point = register.entity_point
        if entity_point == "state":
            interface._set_point_binary_int_on_off(register, interface.turn_on_lights, interface.turn_off_lights)
        elif entity_point == "brightness":
            if isinstance(register.value, int) and 0 <= register.value <= 255:
                interface.change_brightness(register.entity_id, register.value)
            else:
                error_msg = "Brightness value should be an integer between 0 and 255"
                _log.error(error_msg)
                raise ValueError(error_msg)
        else:
            error_msg = f"Unexpected point_name {point_name} for register {register.entity_id}"
            _log.error(error_msg)
            raise ValueError(error_msg)


class SwitchWriteStrategy(WriteStrategy):
    def execute(self, interface, register, point_name):
        entity_point = register.entity_point
        if entity_point == "state":
            normalized = str(register.value).strip().lower()
            if normalized in ("1", "true", "on"):
                interface.set_switch(register.entity_id, "on")
            elif normalized in ("0", "false", "off"):
                interface.set_switch(register.entity_id, "off")
            else:
                error_msg = (
                    f"State value for {register.entity_id} should be "
                    f"true/1/on or false/0/off, got: {register.value}"
                )
                _log.error(error_msg)
                raise ValueError(error_msg)
        else:
            error_msg = f"Only 'state' entity_point is supported for switch entities, got: {entity_point}"
            _log.error(error_msg)
            raise ValueError(error_msg)


class InputBooleanWriteStrategy(WriteStrategy):
    def execute(self, interface, register, point_name):
        entity_point = register.entity_point
        if entity_point == "state":
            interface._set_point_binary_int_on_off(
                register,
                lambda eid: interface.set_input_boolean(eid, "on"),
                lambda eid: interface.set_input_boolean(eid, "off"),
            )
        else:
            _log.info(f"Currently, input_booleans only support state")


class CoverWriteStrategy(WriteStrategy):
    def execute(self, interface, register, point_name):
        entity_point = register.entity_point
        if entity_point == "open/close":
            normalized = str(register.value).strip().lower()
            if normalized == "open":
                interface.set_cover_state(register.entity_id, "open")
            elif normalized == "close":
                interface.set_cover_state(register.entity_id, "close")
            else:
                error_msg = (
                    f"Open/close value for {register.entity_id} should be "
                    f"'open' or 'close', got: {register.value}"
                )
                _log.error(error_msg)
                raise ValueError(error_msg)
        elif entity_point == "position":
            try:
                position = float(register.value)
            except (TypeError, ValueError):
                error_msg = f"Position value for {register.entity_id} should be numeric, got: {register.value}"
                _log.error(error_msg)
                raise ValueError(error_msg)
            if position < 0 or position > 100:
                error_msg = (
                    f"Position value for {register.entity_id} should be between 0 and 100, got: {register.value}"
                )
                _log.error(error_msg)
                raise ValueError(error_msg)
            register.value = int(position) if position.is_integer() else position
            interface.set_cover_position(register.entity_id, register.value)
        else:
            error_msg = (
                f"Only 'open/close' and 'position' entity_point values are supported "
                f"for cover entities, got: {entity_point}"
            )
            _log.error(error_msg)
            raise ValueError(error_msg)


class ClimateWriteStrategy(WriteStrategy):
    def execute(self, interface, register, point_name):
        entity_point = register.entity_point
        if entity_point == "state":
            if isinstance(register.value, int) and register.value in _CLIMATE_VOLTTRON_TO_HVAC_MODE:
                mode = _CLIMATE_VOLTTRON_TO_HVAC_MODE[register.value]
                interface.change_thermostat_mode(entity_id=register.entity_id, mode=mode)
            else:
                error_msg = f"Climate state should be an integer value of 0, 2, 3, or 4"
                _log.error(error_msg)
                raise ValueError(error_msg)
        elif entity_point == "temperature":
            interface.set_thermostat_temperature(entity_id=register.entity_id, temperature=register.value)
        else:
            error_msg = (
                f"Currently set_point is supported only for thermostats state and temperature {register.entity_id}"
            )
            _log.error(error_msg)
            raise ValueError(error_msg)


class Interface(BasicRevert, BaseInterface):
    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)
        self.point_name = None
        self.ip_address = None
        self.access_token = None
        self.port = None
        self.units = None
        self.write_strategies = {
            "light": LightWriteStrategy(),
            "switch": SwitchWriteStrategy(),
            "cover": CoverWriteStrategy(),
            "input_boolean": InputBooleanWriteStrategy(),
            "climate": ClimateWriteStrategy(),
        }
    def _ha_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
    def _ha_base(self):
        return f"http://{self.ip_address}:{self.port}"
    def _ha_post_service(self, service_path, payload, operation_description):
        url = f"{self._ha_base()}/api/services/{service_path}"
        _post_method(url, self._ha_headers(), payload, operation_description)
    def _require_climate_entity(self, entity_id):
        if not entity_id.startswith("climate."):
            _log.error(f"{entity_id} is not a valid thermostat entity ID.")
            return False
        return True
    def _require_cover_entity(self, entity_id):
        if not entity_id.startswith("cover."):
            error_msg = f"{entity_id} is not a valid cover entity ID."
            _log.error(error_msg)
            raise ValueError(error_msg)
    @staticmethod
    def _value_from_entity_data(entity_data, point_key):
        if point_key == "state":
            return entity_data.get("state", None)
        return entity_data.get("attributes", {}).get(point_key, 0)
    def _set_point_binary_int_on_off(self, register, turn_on, turn_off):
        entity_id = register.entity_id
        if not isinstance(register.value, int) or register.value not in (0, 1):
            error_msg = f"State value for {entity_id} should be an integer value of 1 or 0"
            _log.info(error_msg)
            raise ValueError(error_msg)
        if register.value == 1:
            turn_on(entity_id)
        else:
            turn_off(entity_id)
    def _scrape_store_attribute(self, register, entity_data, result):
        entity_point = register.entity_point
        attribute = entity_data.get("attributes", {}).get(entity_point, 0)
        register.value = attribute
        result[register.point_name] = attribute
    def _scrape_store_on_off_numeric(self, register, entity_data, result):
        state = entity_data.get("state", None)
        if state == "on":
            register.value = 1
            result[register.point_name] = 1
        elif state == "off":
            register.value = 0
            result[register.point_name] = 0
    def configure(self, config_dict, registry_config_str):
        self.ip_address = config_dict.get("ip_address", None)
        self.access_token = config_dict.get("access_token", None)
        self.port = config_dict.get("port", None)
        # Check for None values
        if self.ip_address is None:
            _log.error("IP address is not set.")
            raise ValueError("IP address is required.")
        if self.access_token is None:
            _log.error("Access token is not set.")
            raise ValueError("Access token is required.")
        if self.port is None:
            _log.error("Port is not set.")
            raise ValueError("Port is required.")
        self.parse_config(registry_config_str)
    def get_point(self, point_name):
        register = self.get_register_by_name(point_name)
        entity_data = self.get_entity_data(register.entity_id)
        return self._value_from_entity_data(entity_data, register.point_name)
    def _set_point(self, point_name, value):
        register = self.get_register_by_name(point_name)
        if register.read_only:
            raise IOError(
                "Trying to write to a point configured read only: " + point_name)
        try:
            register.value = register.reg_type(value)
        except (TypeError, ValueError):
            if parse_domain(register.entity_id) == "cover" and register.entity_point == "position":
                error_msg = f"Position value for {register.entity_id} should be numeric and between 0 and 100, got: {value}"
                _log.error(error_msg)
                raise ValueError(error_msg)
            raise
        domain = parse_domain(register.entity_id)
        if domain in self.write_strategies:
            self.write_strategies[domain].execute(self, register, point_name)
        else:
            error_msg = (
                f"Unsupported entity_id: {register.entity_id}. "
                f"Currently set_point is supported only for lights, switches, input_booleans, covers, and thermostats"
            )
            _log.error(error_msg)
            raise ValueError(error_msg)
        return register.value

    def get_entity_data(self, point_name):
        headers = self._ha_headers()
        # the /states grabs current state AND attributes of a specific entity
        url = f"{self._ha_base()}/api/states/{point_name}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()  # return the json attributes from entity
        else:
            error_msg = (f"Request failed with status code {response.status_code}, Point name: {point_name}, "
                         f"response: {response.text}")
            _log.error(error_msg)
            raise Exception(error_msg)
    def _scrape_all(self):
        result = {}
        read_registers = self.get_registers_by_type("byte", True)
        write_registers = self.get_registers_by_type("byte", False)
        for register in read_registers + write_registers:
            entity_id = register.entity_id
            entity_point = register.entity_point
            try:
                entity_data = self.get_entity_data(entity_id)  # Using Entity ID to get data
                if "climate." in entity_id:
                    if entity_point == "state":
                        state = entity_data.get("state", None)
                        if state in _CLIMATE_HA_STATE_TO_VOLTTRON:
                            val = _CLIMATE_HA_STATE_TO_VOLTTRON[state]
                            register.value = val
                            result[register.point_name] = val
                        else:
                            error_msg = f"State {state} from {entity_id} is not yet supported"
                            _log.error(error_msg)
                            raise ValueError(error_msg)
                    else:
                        self._scrape_store_attribute(register, entity_data, result)
                elif ("switch." in entity_id or "light." in entity_id
                        or "input_boolean." in entity_id):
                    if entity_point == "state":
                        self._scrape_store_on_off_numeric(register, entity_data, result)
                    else:
                        self._scrape_store_attribute(register, entity_data, result)
                else:
                    if entity_point == "state":
                        state = entity_data.get("state", None)
                        register.value = state
                        result[register.point_name] = state
                    else:
                        self._scrape_store_attribute(register, entity_data, result)
            except Exception as e:
                _log.error(f"An unexpected error occurred for entity_id: {entity_id}: {e}")
        return result
    def parse_config(self, config_dict):
        if config_dict is None:
            return
        for regDef in config_dict:
            if not regDef['Entity ID']:
                continue
            read_only = str(regDef.get('Writable', '')).lower() != 'true'
            entity_id = regDef['Entity ID']
            entity_point = regDef['Entity Point']
            self.point_name = regDef['Volttron Point Name']
            self.units = regDef['Units']
            description = regDef.get('Notes', '')
            default_value = ("Starting Value")
            type_name = regDef.get("Type", 'string')
            reg_type = type_mapping.get(type_name, str)
            attributes = regDef.get('Attributes', {})
            register_type = HomeAssistantRegister
            register = register_type(
                read_only,
                self.point_name,
                self.units,
                reg_type,
                attributes,
                entity_id,
                entity_point,
                default_value=default_value,
                description=description)
            if default_value is not None:
                self.set_default(self.point_name, register.value)
            self.insert_register(register)
    def turn_off_lights(self, entity_id):
        self._ha_post_service(
            "light/turn_off",
            {"entity_id": entity_id},
            f"turn off {entity_id}",
        )
    def turn_on_lights(self, entity_id):
        self._ha_post_service(
            "light/turn_on",
            {"entity_id": entity_id},
            f"turn on {entity_id}",
        )
    def change_thermostat_mode(self, entity_id, mode):
        if not self._require_climate_entity(entity_id):
            return
        self._ha_post_service(
            "climate/set_hvac_mode",
            {"entity_id": entity_id, "hvac_mode": mode},
            f"change mode of {entity_id} to {mode}",
        )
    def set_thermostat_temperature(self, entity_id, temperature):
        if not self._require_climate_entity(entity_id):
            return
        if self.units == "C":
            converted_temp = round((temperature - 32) * 5/9, 1)
            _log.info(f"Converted temperature {converted_temp}")
            temp_payload = converted_temp
        else:
            temp_payload = temperature
        self._ha_post_service(
            "climate/set_temperature",
            {"entity_id": entity_id, "temperature": temp_payload},
            f"set temperature of {entity_id} to {temperature}",
        )
    def change_brightness(self, entity_id, value):
        # ranges from 0 - 255
        self._ha_post_service(
            "light/turn_on",
            {"entity_id": entity_id, "brightness": value},
            f"set brightness of {entity_id} to {value}",
        )
    def set_switch(self, entity_id, state):
        service = 'turn_on' if state == 'on' else 'turn_off'
        self._ha_post_service(
            f"switch/{service}",
            {"entity_id": entity_id},
            f"{service} {entity_id}",
        )
    def set_cover_state(self, entity_id, state):
        self._require_cover_entity(entity_id)
        service = "open_cover" if state == "open" else "close_cover"
        self._ha_post_service(
            f"cover/{service}",
            {"entity_id": entity_id},
            f"{service} {entity_id}",
        )
    def set_cover_position(self, entity_id, position):
        self._require_cover_entity(entity_id)
        self._ha_post_service(
            "cover/set_cover_position",
            {"entity_id": entity_id, "position": position},
            f"set position of {entity_id} to {position}",
        )
    def set_input_boolean(self, entity_id, state):
        service = 'turn_on' if state == 'on' else 'turn_off'
        self._ha_post_service(
            f"input_boolean/{service}",
            {"entity_id": entity_id},
            f"{service} input_boolean {entity_id}",
        )
