# Sprint 3 — GitHub Project Board Items (PBIs & Tasks)

Use this document to create **GitHub Issues** and add them to your **Sprint 3** project view.  
Suggested column flow: **Backlog → In Progress → Done**.

**Tip:** Create issues from each **Title** block; paste **Description** and **Acceptance criteria** into the issue body. Use labels such as `PBI`, `Task`, `area:home-assistant`, `sprint-3`.

---

## Development

### PBI-1 — Implement switch write (cleanup + merge)

**Type:** PBI  
**Title:** `[PBI] Home Assistant driver — switch write (cleanup + merge)`

**Description**

Implement and consolidate **switch** entity writes for the `home_assistant` interface: normalize on/off inputs, call Home Assistant `switch.turn_on` / `switch.turn_off` via REST, and remove duplicate HTTP/header logic where possible.

**Acceptance criteria**

- [ ] Writable registry rows with `Entity ID` under domain `switch.` and `Entity Point` `state` accept valid values (`true`/`false`/`on`/`off`/`1`/`0` as supported by code).
- [ ] Invalid values raise a clear error and do not send a service call.
- [ ] Outgoing REST calls use the correct `/api/services/switch/turn_on` or `.../turn_off` URL and JSON body (`entity_id`).
- [ ] Code is aligned with shared helpers (e.g. `_ha_post_service`) where applicable.

**References**

- `platform_driver/interfaces/home_assistant.py` — `SwitchWriteStrategy`, `set_switch`

---

### PBI-2 — Implement cover write (full logic)

**Type:** PBI  
**Title:** `[PBI] Home Assistant driver — cover write (full logic)`

**Description**

Complete **cover** support: **open** / **close** map to `cover.open_cover` / `cover.close_cover`; **position** maps to `cover.set_cover_position` with validation.

**Acceptance criteria**

- [ ] `open` / `close` (case-insensitive) trigger the correct HA services.
- [ ] Position accepts numeric values in **0–100**; non-numeric or out-of-range values raise `ValueError` before POST.
- [ ] REST URLs and JSON payloads match Home Assistant REST API expectations.

**References**

- `platform_driver/interfaces/home_assistant.py` — `CoverWriteStrategy`, `set_cover_state`, `set_cover_position`

---

### TASK-1 — Refactor `_set_point` using Strategy pattern

**Type:** Task  
**Title:** `[Task] Refactor home_assistant _set_point — Strategy pattern`

**Description**

Replace a long `if/elif` chain on entity type with **domain → strategy** dispatch: parse HA domain from `entity_id`, look up `write_strategies[domain]`, call `execute(interface, register, point_name)`, with fallback for unsupported domains.

**Acceptance criteria**

- [ ] `parse_domain(entity_id)` extracts the domain prefix (e.g. `cover` from `cover.garage`).
- [ ] `self.write_strategies` maps domains (`light`, `switch`, `cover`, `input_boolean`, `climate`) to strategy instances.
- [ ] Unsupported domains fail with a single, clear error path.
- [ ] Behavior for existing domains matches pre-refactor semantics (regression covered by tests where possible).

**References**

- `platform_driver/interfaces/home_assistant.py` — `WriteStrategy`, concrete strategies, `Interface._set_point`

---

## Testing

### TASK-2 — Unit tests + mock HA setup (switch, cover, driver integration)

**Type:** Task  
**Title:** `[Task] Home Assistant tests — unit (switch/cover) + mock HA + integration`

**Description**

Single testing deliverable: **(1)** **pytest** unit tests that mock `requests.post` and assert **URL** + **JSON** for **switch** and **cover** writes; **(2)** mock **integration** tests that run **`DriverAgent` + `setup_device()`** with mocked `requests` (driver → API → response); **(3)** documented **testing strategy** (`PYTHONPATH`, `--noconftest`, optional live HA). No real Home Assistant required for (1) and (2).

**Acceptance criteria — unit (switch & cover)**

- [ ] Switch: `true`/on → `switch/turn_on`; `false`/off → `switch/turn_off`; invalid → `ValueError`, no POST.
- [ ] Cover: open/close → `cover/open_cover` / `cover/close_cover`; position → `cover/set_cover_position`; invalid position → `ValueError`, no POST.

**Acceptance criteria — mock HA & integration**

- [ ] Unit suite runs with `PYTHONPATH=PlatformDriverAgent` and `pytest --noconftest` where platform conftest is unavailable (e.g. Windows).
- [ ] Mock integration suite runs with `PYTHONPATH` = **Volttron repo root** + **PlatformDriverAgent**; exercises `set_point` / `get_point` through `DriverAgent` with mocked HTTP.
- [ ] Testing strategy documented in-repo (`docs/Testing-Strategy-Home-Assistant.md`) for team/Wiki handoff.

**References**

- `tests/test_home_assistant_unit.py` — `TestHomeAssistantSwitchWrites`, `TestHomeAssistantCoverWrites`
- `tests/test_home_assistant_integration_mock.py`
- `docs/Testing-Strategy-Home-Assistant.md`

---

## Documentation

### TASK-3 — Update README and Wiki (domains + testing & usage)

**Type:** Task  
**Title:** `[Task] README & Wiki — Home Assistant domains, testing strategy, usage`

**Description**

Deliver in-repo and Wiki documentation as one work item: **README** lists supported `home_assistant` domains and configuration; **GitHub Wiki** (or linked repo doc) covers **testing strategy** and how to run tests / use the driver.

**Acceptance criteria — README**

- [ ] `driver_type: home_assistant` and required **driver_config** keys are documented.
- [ ] Domains `light`, `switch`, `input_boolean`, `cover`, `climate` and key **Entity Point** values are listed.
- [ ] Notes on `get_point` / Volttron point naming vs HA `state` vs `attributes`.

**Acceptance criteria — Wiki (or equivalent)**

- [ ] **Testing Strategy** section populated: unit, mock integration, optional live HA; copy-paste commands (Windows/PowerShell and Linux where relevant).
- [ ] States that **mocked** driver→API→response tests count as integration where applicable (e.g. course/bonus).
- [ ] Usage pointers align with README (link to `README.md` or duplicate short “how to configure” if Wiki is the primary entry).

**References**

- `README.md` (PlatformDriverAgent)
- `docs/Testing-Strategy-Home-Assistant.md` (paste into Wiki or link from Wiki)

---

## Summary checklist (Sprint 3 board)

| ID | Track | Title (short) |
|----|--------|----------------|
| PBI-1 | Development | Switch write (cleanup + merge) |
| PBI-2 | Development | Cover write (full logic) |
| TASK-1 | Development | Refactor `_set_point` — Strategy |
| TASK-2 | Testing | Unit + mock HA + integration + strategy doc |
| TASK-3 | Documentation | README & Wiki — domains + testing/usage |

---

## Optional GitHub labels

- `PBI`, `Task`, `sprint-3`, `home-assistant`, `platform-driver`, `testing`, `documentation`
