# Platform Driver Agent

The Platform Driver agent is a special purpose agent a user can install on the platform to manage communication of the 
platform with devices. The Platform driver features a number of endpoints for collecting data and sending control signals 
using the message bus and automatically publishes data to the bus on a specified interval.

## Dependencies

VOLTTRON drivers operated by the platform driver may have additional requirements for installation. Required libraries:
1. BACnet driver - bacpypes
2. Modbus driver - pymodbus
3. Modbus_TK driver - modbus-tk
4. DNP3 and IEEE 2030.5 drivers - pydnp3

The easiest way to install the requirements for drivers included in the VOLTTRON repository is to use bootstrap.py 
```
python3 bootstrap.py --drivers
```

## Configuration

### Agent Configuration

The Platform Driver Agent configuration consists of general settings for all devices. The default values of the 
Platform Driver should be sufficient for most users. The user may optionally change the interval between device scrapes 
with the driver_scrape_interval.

The following example sets the driver_scrape_interval to 0.05 seconds or 20 devices per second:
```
{
    "driver_scrape_interval": 0.05,
    "publish_breadth_first_all": false,
    "publish_depth_first": false,
    "publish_breadth_first": false,
    "publish_depth_first_all": true,
    "group_offset_interval": 0.0
}
```

1. driver_scrape_interval - Sets the interval between devices scrapes. Defaults to 0.02 or 50 devices per second. 
Useful for when the platform scrapes too many devices at once resulting in failed scrapes.
2. group_offset_interval - Sets the interval between when groups of devices are scraped. Has no effect if all devices 
are in the same group.
In order to improve the scalability of the platform unneeded device state publishes for all devices can be turned off. 
All of the following setting are optional and default to True.
3. publish_depth_first_all - Enable “depth first” publish of all points to a single topic for all devices.
4. publish_breadth_first_all - Enable “breadth first” publish of all points to a single topic for all devices.
5. publish_depth_first - Enable “depth first” device state publishes for each register on the device for all devices.
6. publish_breadth_first - Enable “breadth first” device state publishes for each register on the device for all devices.

### Driver Configuration
Each device configuration has the following form:
```
{
    "driver_config": {"device_address": "10.1.1.5",
                      "device_id": 500},
    "driver_type": "bacnet",
    "registry_config":"config://registry_configs/vav.csv",
    "interval": 60,
    "heart_beat_point": "heartbeat",
    "group": 0
}
```
The following settings are required for all device configurations:
1. driver_config - Driver specific setting go here. See below for driver specific settings.
2. driver_type - Type of driver to use for this device: bacnet, modbus, fake, home_assistant, etc.
3. registry_config - Reference to a configuration file in the configuration store for registers on the device. 

These settings are optional:

1. interval - Period which to scrape the device and publish the results in seconds. Defaults to 60 seconds.
2. heart_beat_point - A Point which to toggle to indicate a heartbeat to the device. A point with this 
Volttron Point Name must exist in the registry. If this setting is missing the driver will not send a heart beat signal 
to the device. Heart beats are triggered by the Actuator Agent which must be running to use this feature.
3. group - Group this device belongs to. Defaults to 0

### Home Assistant driver (`home_assistant`)

The Home Assistant interface talks to a local Home Assistant instance over the REST API (`requests`). Core VOLTTRON already includes `requests`; no extra driver package is required beyond a valid long-lived access token in Home Assistant.

#### `driver_config`

| Key | Description |
|-----|-------------|
| `ip_address` | Hostname or IP of Home Assistant (required). |
| `port` | HTTP port (required), e.g. `8123`. |
| `access_token` | Long-lived access token (required). |

Example fragment:

```json
"driver_config": {
    "ip_address": "192.168.1.10",
    "port": 8123,
    "access_token": "YOUR_LONG_LIVED_TOKEN"
}
```

#### Registry format

Registry entries are JSON objects (often loaded via the configuration store). Typical fields include:

- **Entity ID** — Home Assistant entity id (e.g. `light.kitchen`, `cover.garage`).
- **Entity Point** — Which part of the entity to read or write (see supported domains below).
- **Volttron Point Name** — VOLTTRON point name used with `get_point` / `set_point` / scrape results.
- **Writable** — `true` / `false` for write access.
- **Type** — `string`, `int`, `float`, `bool`, etc. (maps to Python types for values).

**Note:** `get_point` resolves the HA field using the **Volttron Point Name**: if that name is `state`, the driver reads HA’s `state` string; otherwise it reads `attributes[Volttron Point Name]`. Align naming with how you want to address HA data.

#### Supported Home Assistant domains

Entity support is determined by the **domain** prefix of **Entity ID** (the part before the first `.`). Domains with first-class **write** handling (strategy-based `set_point`) are:

| Domain | `set_point` / Entity Point | Notes |
|--------|----------------------------|--------|
| **light** | `state` | `0` / `1` → light off / on (`light.turn_off` / `light.turn_on`). |
| **light** | `brightness` | Integer `0`–`255` → `light.turn_on` with `brightness`. |
| **switch** | `state` | `true` / `false` / `on` / `off` / `1` / `0` (string forms) → `switch.turn_on` / `switch.turn_off`. |
| **input_boolean** | `state` | `0` / `1` → `input_boolean.turn_off` / `input_boolean.turn_on`. Other entity points log only. |
| **cover** | `open/close` | `open` / `close` → `cover.open_cover` / `cover.close_cover`. |
| **cover** | `position` | Numeric `0`–`100` → `cover.set_cover_position`. Non-numeric or out-of-range values raise `ValueError`. |
| **climate** | `state` | Integer mode codes `0` off, `2` heat, `3` cool, `4` auto → `climate.set_hvac_mode`. |
| **climate** | `temperature` | Setpoint → `climate.set_temperature` (if registry **Units** is `C`, values are treated as °F and converted to °C for the API). |

Any **Entity ID** whose domain is **not** in the table above is rejected for `set_point` with a clear error. Other domains may still appear in the registry for **read/scrape** if you configure **Entity Point** appropriately (see below).

#### Read / scrape (`scrape_all`)

- **climate.*** — `state` is mapped to numeric modes (`off`→0, `heat`→2, `cool`→3, `auto`→4); other **Entity Point** values come from HA **attributes** by name.
- **switch.*** / **light.*** / **input_boolean.*** — `state` is normalized to `1` / `0` for on/off; other points use **attributes**.
- **cover.*** and other domains — `state` returns the raw HA state string; other **Entity Point** values use **attributes**.

For questions or examples, see `services/core/PlatformDriverAgent/tests/test_home_assistant.py` (live instance) and `tests/test_home_assistant_unit.py` / `tests/test_home_assistant_integration_mock.py` (mocked HTTP).
