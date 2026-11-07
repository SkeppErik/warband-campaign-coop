# Warband Campaign Co-op: plan

Goal: the whole Mount & Blade: Warband single-player campaign in co-op, written from scratch. Every feature works
like single player; anything that differs is listed in the README.

## Independence rules

This mod is not a fork of any other co-op mod and uses none of their code.

- Built only from: TaleWorlds' Native module system (official download), WSE2 (official release, its SDK and
  documentation), libraries under permissive licenses (e.g. ENet, MIT), and our own reverse-engineering of the
  game executable.
- Other co-op projects' code is archived offline and is not opened while writing this one. Nothing is copied or
  adapted from them, and each system here is designed fresh (protocol, save format, battle hand-off).
- Allowed to carry over: knowledge of how native single player behaves, our own engine findings (addresses,
  crash causes), and our own test tooling ideas.

## Architecture

| Layer | What | Notes |
|---|---|---|
| Module | Native module system 1.171 + WSE2 addons, plus our co-op code in its own files (`module_fc_*.py`) | Native's campaign rules run on the server unchanged wherever possible |
| Campaign server | WSE2 dedicated campaign server: the one world, native simulation, saves | Players' parties are WSE2 player parties |
| Clients | Warband + WSE2, connected to the campaign server | Show the map, menus and screens; send the player's choices |
| Protocol | One documented message set (`docs/protocol.md`): every message has an id, fields, direction, sender checks | Designed up front, versioned |
| Characters | One store per player, keyed by Steam id, with a single field registry and a schema version | Every saved field is declared once; nothing is dropped by a save (lesson from the old fork's save bug) |
| Battles | Phase 1: local battles on the client, results applied by the server. Phase 2: shared battles on dedicated battle servers with our own hand-off | Our engine findings cover keeping the connection through a local mission |
| Native helper | A small client DLL, only where the engine forces it (game-type checks around local missions and conversations) | Loaded through WSE2's plugin support if possible, else a permissively licensed ASI loader |

## Milestones

Each milestone ends with a build, and with an in-game check only when the owner says go.

- **M0 Clean base:** official module system + WSE2 addons build; build script; a clean test copy of the game
  (copied from the Steam install, WSE2 added, nothing from other mods).
- **M1 Shared map:** dedicated campaign server, two clients on one map with their own parties; joining, leaving.
- **M2 Characters and saves:** identity, character creation, the character store, world save and restore, rejoin.
- **M3 Life on the map:** clock and pause rules, encounters and their menus, talking to parties, towns and villages
  (trade, recruit, tavern), party upkeep (food, morale, wages, desertion), prisoners.
- **M4 Local battles:** fight on your own client, casualties/XP/loot/prisoners applied as native does.
- **M5 Shared battles:** players fight together on a battle server.
- **M6 Our features, rebuilt:** joining battles under way, raiding villages, conversations on the map, sieges
  (camp, equipment, assaults, sallies, defence), save and rejoin for all of them.
- **M7 The rest of the campaign:** arena, tournaments, training grounds, quests, courtship, companions, kingdoms
  (mercenary, vassal, fiefs, marshals), enterprises.
- **M8 Ship:** an installer package friends can use, a one-click host and join.

## Build design

The repository holds no TaleWorlds or WSE2 files. `tools/build.py` unpacks the official module system, applies the
WSE2 SDK as its README describes, and replaces each native list file with a wrapper that runs the native list
through our patches (`tools/fcpatch.py`, patches in `src/`). New troops and parties are appended after native's, so
native ids never move. The order of global variables is pinned in `src/variables.txt` (part of the save format).

## Open questions for M1 (check in game)

- Does WSE2's campaign server fire `ti_on_player_join` / `ti_on_player_exit` as simple triggers, with the player
  in trigger parameter 1? (`src/fc_players.py` assumes so.)
- How a dedicated campaign server starts its world (native `game_start`, a new or a loaded save) and what a
  connecting client is shown before it has a party.
- Whether the client follows its own party on the map by itself or needs to be told.
- Our slot numbers (`fc_slot_*` = 900+) must not collide with native's: add a build check once the module system
  is in.

## Needed before M0

- TaleWorlds Mount&Blade Warband Module System (1.171 or the latest official), from taleworlds.com.
- WSE2 (the version matching Warband 1.174) from the author's official release.
