# Testing Strategy — Home Assistant Driver

This document describes how we test the `home_assistant` platform driver interface: **unit tests**, **mocked integration tests**, and **optional end-to-end tests** against a real Home Assistant instance. It aligns with the team backlog (switch/cover writes, strategy-based `_set_point`, mock HA setup, and documentation).

---

## Goals

| Goal | How we address it |
|------|-------------------|
| Verify **switch** write behavior (`turn_on` / `turn_off`, invalid input → error) | Unit tests assert outgoing REST calls. |
| Verify **cover** write behavior (`open_cover` / `close_cover` / `set_cover_position`, invalid position → error) | Same. |
| Avoid requiring a live Home Assistant for CI and local dev | Mock `requests.post` / `requests.get` at the interface (or below). |
| Still exercise the **driver → HTTP → response** path for bonus / integration credit | Mocked tests drive `DriverAgent.set_point` / `get_point` with real `setup_device()`. |
| Optional validation against real HA | `test_home_assistant.py` when IP, token, and port are configured. |

---

## Test layers

### 1. Unit tests (interface, mock HTTP)

**File:** `services/core/PlatformDriverAgent/tests/test_home_assistant_unit.py`

- Instantiates `platform_driver.interfaces.home_assistant.Interface` directly with minimal registry rows (`HomeAssistantRegister`).
- Patches **`platform_driver.interfaces.home_assistant.requests.post`** so **no real HTTP** is sent.
- **Assertions:** for each scenario, verify the **URL** (full `http://{ip}:{port}/api/services/...`) and the **`json=` payload** passed to `requests.post`.
- **Coverage (minimum):**
  - **Switch:** `true` → `POST .../switch/turn_on`; `false` → `.../switch/turn_off`; invalid string → `ValueError`, **no** POST.
  - **Cover:** `open` / `close` → `cover/open_cover` / `cover/close_cover`; position `50` → `cover/set_cover_position` with `position` in body; non-numeric or out-of-range → `ValueError`, no POST.

**Run (Windows-friendly, no Volttron platform conftest):**

```powershell
cd services\core\PlatformDriverAgent
$env:PYTHONPATH = (Get-Location).Path
python -m pytest tests/test_home_assistant_unit.py --noconftest -v
```

`--noconftest` skips `PlatformDriverAgent/conftest.py`, which pulls in full-platform fixtures (often **Linux-only** dependencies such as `grp`).

---

### 2. Mock integration tests (driver → API → response handling)

**File:** `services/core/PlatformDriverAgent/tests/test_home_assistant_integration_mock.py`

- Uses real **`DriverAgent`** and **`setup_device()`** so the same **module load + `configure` + registry** path as production is exercised.
- Still **mocks** `requests.post` / `requests.get` on the `home_assistant` module (no real Home Assistant).
- **POST path:** `agent.set_point(...)` → `interface.set_point` → `_post_method` → `requests.post`. Assert URL + JSON body; optionally assert return value is populated on success.
- **Response handling:** configure mock to return **non-2xx** status (e.g. `400`); expect an **exception** after `set_point` (driver surfaces interface / `_post_method` errors).
- **GET path:** `agent.get_point(...)` with a registry row whose Volttron point name matches how `get_point` resolves HA fields (e.g. point name `state` for raw HA `state`); mock `requests.get` and assert URL and parsed return value.

**Run:** `PYTHONPATH` must include **both** the **Volttron repository root** and **PlatformDriverAgent** (so `volttron` and `platform_driver` import correctly):

```powershell
$root = "C:\path\to\volttron"
$pda = "$root\services\core\PlatformDriverAgent"
$env:PYTHONPATH = "$root;$pda"
Set-Location $pda
python -m pytest tests/test_home_assistant_integration_mock.py --noconftest -v
```

If `volttron` is not on `PYTHONPATH`, `pytest.importorskip` causes this module to be **skipped** at collection time.

---

### 3. Live Home Assistant integration tests (optional)

**File:** `services/core/PlatformDriverAgent/tests/test_home_assistant.py`

- Full **Platform Driver** + RPC + configuration store flow; requires a **running VOLTTRON platform** and compatible environment (typically **Linux** or WSL).
- Tests are **skipped** unless `HOMEASSISTANT_TEST_IP`, `ACCESS_TOKEN`, and `PORT` are set in that file (or refactored to environment variables).
- Requires real entities (e.g. `input_boolean.volttrontest`, `cover.test_cover`) as described in the test module comments.

Use this tier for **manual / staging** validation, not as a gate for developers on Windows without WSL.

---

## Mock Home Assistant setup (summary)

We do **not** run a Home Assistant container in CI for these tests. Instead:

1. **Patch `requests`** where the interface issues REST calls (`post` for services, `get` for `/api/states/...`).
2. Return a **`MagicMock`** with `status_code=200` for success paths so `_post_method` / `get_entity_data` do not raise.
3. For error-path tests, return **non-200** and assert exceptions.

This satisfies course guidance: **mocked calls still count as integration** when the **driver → API → response** chain is under test.

---

## Relationship to design / refactor

- **`_set_point`** is routed by **Home Assistant domain** (`parse_domain`) through a **`write_strategies`** map (**Strategy pattern**). Unit tests indirectly validate behavior per domain (switch, cover, etc.) without depending on strategy class names in assertions.
- **README** (`services/core/PlatformDriverAgent/README.md`) lists **supported domains** and entity points; tests should stay consistent with that table.

---

## Quick command reference

| Suite | Command (after setting `PYTHONPATH` as above) |
|-------|-----------------------------------------------|
| Unit only | `pytest tests/test_home_assistant_unit.py --noconftest -v` |
| Mock integration only | `pytest tests/test_home_assistant_integration_mock.py --noconftest -v` |
| Both (local) | `pytest tests/test_home_assistant_unit.py tests/test_home_assistant_integration_mock.py --noconftest -v` |

---

## Wiki usage

Copy this page into the GitHub Wiki under **Testing Strategy**, or link to this file in the repository at:

`services/core/PlatformDriverAgent/docs/Testing-Strategy-Home-Assistant.md`
