---
name: home-assistant-sensors
title: Home Assistant through its connector
description: Use when the person asks about their Home Assistant (a home, lab or greenhouse it monitors), such as what sensors and devices exist, current readings, how a reading changed over time, turning something on or off, or an automation, script, scene, helper or dashboard. Triggers on "my Home Assistant", "the temperature sensor in", "history of", "turn on the", "make an automation that".
keywords: [home assistant, sensors, entities, state, history, statistics, service call, automation, level:L2]
---

# Home Assistant through its connector

The Home Assistant connector talks to the person's own Home Assistant at the
address and with the access token they set in the connector. Everything you
see and change is their live system.

## Find the entities, never guess them

- `ha_get_overview` (start with `detail_level: "minimal"`, narrow with
  `domains`) shows what exists by domain; `ha_search` finds entities by name,
  area, floor or domain, and with an exact entity id it lists the automations,
  scripts and scenes that use it.
- `ha_list_floors_areas`, `ha_get_entity` and `ha_get_device` give where a
  sensor is and what it belongs to. Use the entity ids these return; an id you
  composed may name nothing.

## Read values and their history

- `ha_get_state` reads one or many entities now; ask only for the `fields` or
  `attribute_keys` you need. Report the value with its unit and when it last
  changed (`last_changed`); `unavailable` or `unknown` is a state, not a zero.
- `ha_get_history` gives `source: "history"` (every state change, kept as long as
  the recorder keeps it, ten days by default) or `source: "statistics"` (long-term aggregates, only for
  sensors with a state class) between `start_time` and `end_time` (a look-back
  such as a number of hours or days, or a local time).
- For analysis, write the series to a file in the workspace (time, value,
  unit, entity id) and work on the file: plot it, compare sensors, find gaps.
  Say how many points came back and over which span; a sensor that reports only
  on change has uneven spacing.

## Change things deliberately

- `ha_call_service` (or `ha_bulk_control` for several entities) acts on real
  devices. Do what the person asked, on the entities they meant, then read the
  state back with `ha_get_state` to confirm it.
- For automations, scripts, scenes, helpers, dashboards, renames and backups,
  load the `home-assistant-best-practices` skill first and follow it. The
  `ha_config_get_*` / `ha_config_set_*` tools read and write them; after a change,
  `ha_get_automation_traces` shows whether an automation ran as intended.
- Before renaming or removing anything, check what uses it with `ha_search` on
  the exact entity id.

## When it cannot reach Home Assistant

The connector starts the server with the person's address and token. If a call
says Home Assistant could not be reached or the token was refused, say exactly
that; the address and token are changed in the connector's settings, and you
never ask for a token in the conversation.
