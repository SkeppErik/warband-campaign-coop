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
  (copied from the Steam install, WSE2 added, nothing from other mods). **Done 2026-11-07:** the full build runs
  against module system 1.171 and the official WSE2 SDK; `tools/install.py` puts it into the test copy.
- **M1 Shared map:** dedicated campaign server, two clients on one map with their own parties; joining, leaving.
  **Built 2026-11-07; first in-game checks by the owner:** the server runs its world; WSE2's "Join a Campaign"
  button works (module ships `module_config_template.ini`, `docs/wse2-join.md`) and the client reaches the server;
  our join trigger fires. The first join crashed the server (party_clear on a player party, fixed, not re-checked).
  Still to see in game: the player's party on the map, the camera following it, two players (needs two PCs:
  one WSE2 client per Windows session).
- **M2 Characters and saves:** identity, character creation, the character store, world save and restore, rejoin.
  **Part 1 built 2026-11-07, not tested:** a character (pool troop + party) is bound to the player's unique id on
  first join; rejoining gives the same troop and party back where they were; the server saves the world
  (`auto_save` into its `--save-no` slot) when a player leaves and once a game day, and `fc_server.bat` continues
  it with `--load-game`. Open: character creation (native's start menus on a campaign client), what a new player
  starts with, more characters than pool slots, a separate character store (moving characters between worlds).
  **Owner's check 2026-11-07:** join, leave and rejoin work and the party comes back where it was; the world saves
  on leave. Found: the client ran native's world triggers (script errors) -> guarded to server/single player;
  bandits locked a player's party in repeated simulated battles -> AI no longer targets player parties until M3;
  the client showed the training field until its party arrived -> joining screen. Owner confirmed all three fixed.
- **M3 Life on the map:** clock and pause rules, encounters and their menus, talking to parties, towns and villages
  (trade, recruit, tavern), party upkeep (food, morale, wages, desertion), prisoners.
  **Part 1 built 2026-11-08; owner checked in a village: right text and options, world-only options work.** Native
  menus run on the server for the player and show on the client
  (`docs/encounters.md`, `src/fc_menus.py`): reaching a town, village or party opens native's menu; options work
  where they only change the world (recruiting, leaving, menu to menu); missions, trade/loot screens,
  conversations and waiting say "not available in co-op yet". Native code's messages reach the player.
  **Part 2 built 2026-11-08, owner checked: trade from town menus and the own inventory window work** (loot from menus
  built, not seen yet) (items and
  gold synced, checked by the server; `docs/encounters.md` "Items").
  **Part 3 built 2026-11-08, not tested: conversations** started from the map and menus (party encounters, castle
  meetings), native dialogs run on the server, shown as a text menu (`docs/encounters.md` "Conversations").
- **M4 Local battles:** fight on your own client, casualties/XP/loot/prisoners applied as native does.
- **M5 Shared battles:** players fight together on a battle server.
- **M6 Our features, rebuilt:** joining battles under way, raiding villages, conversations on the map, sieges
  (camp, equipment, assaults, sallies, defence), save and rejoin for all of them.
- **M7 The rest of the campaign:** arena, tournaments, training grounds, quests, courtship, companions, kingdoms
  (mercenary, vassal, fiefs, marshals), enterprises.
- **M8 Ship:** an installer package friends can use, a one-click host and join.

## Deviations from single player

Everything should work as native does; what doesn't is listed here (temporary ones go away with their milestone).

- The campaign clock keeps running while a player is in a battle (battle design, below).
- Temporary until M3: AI parties never choose a player's party as a target (`src/fc_authority.py`,
  `game_check_party_sees_party`), because the server has no encounter for player parties yet.
- At most `fc_max_players` (16) different people per world: each gets a pool character for good.
- A joining player sees a "Joining the campaign" screen for a moment (the server tells the client its party).
- Time doesn't stop in menus (a player in a menu stays where they are; the world goes on).
- Menu globals (147, listed by the build in `fc_menu_globals.txt`) are kept per player: what one player's menus
  set (honour, kingdom choices, town visit state...) is theirs, and world triggers see the world's copy.
- Temporary until M4: a battle event with a player's party is never auto-resolved (the player chooses in the menu).
- Trade prices don't rise while you keep buying in one visit; they change when the trade is done.
- Conversations show as a text menu (the NPC's line and your answers), not the 3D conversation screen.

## Battle design (decided 2026-11-07)

1. Player A meets an enemy on the map and chooses to fight.
2. Every other player within `fc_join_distance` of the fight is offered to join, on A's side.
3. Whoever accepts fights on A's side; each player commands their own troops (A orders A's soldiers, B orders B's).
4. Whoever declines, or is too far away, carries on with the campaign as normal while the battle runs.
5. `fc_join_distance` is unlimited while testing.

Recommended details (owner to confirm):
- One path for every battle, solo or joined: the battle runs on a battle server, and the campaign connection stays
  open (our engine finding), so nobody disconnects.
- The offer goes out when the battle starts; a player can also join while it runs, if still in range and not busy
  (a menu, another fight).
- The parties in the fight stay frozen on the map. The campaign clock keeps running for everyone else (a
  difference from single player, where a battle takes no time).
- Each player's party takes its own casualties and gets its own XP, loot and prisoners, split by contribution as
  native splits a victory with allies.
- Commanding your own troops: the engine can assign soldiers to a player for orders; confirm when building M5.

## Build design

The repository holds no TaleWorlds or WSE2 files. `tools/build.py` unpacks the official module system, applies the
WSE2 SDK as its README describes, and replaces each native list file with a wrapper that runs the native list
through our patches (`tools/fcpatch.py`, patches in `src/`). New troops and parties are appended after native's, so
native ids never move. The order of global variables is pinned in `src/variables.txt` (part of the save format).

## M1 questions: answers (reverse engineering of the WSE2 exes, `docs/wse2-join.md`)

- `ti_server_player_joined` / `ti_on_player_exit` fire on the campaign server as simple triggers, player in
  trigger parameter 1 (joined: seen in game; exit: `mbnetNetworkServer::disconnectPlayer`).
- The server starts its world with native `game_start` (`mbGame::start`), or loads save slot `--save-no N` with
  `--load-game`.
- A client is told its party by the engine (`player_set_party_id` sends it; the client sets its main party). Our
  `fc_msg_your_party` + `set_camera_follow_party` stays as a sure way to point the camera.
- `game_receive_network_message` (mapped script 0x27) runs on a campaign client for script events; nothing checks
  the game type.
- The server config is enough to start the world; the "Join a Campaign" button loads the campaign data and then
  shows the server list (Internet / LAN / Favorites).
- Two clients on one PC: no ("WSE2 Mutex", one per Windows session).
- Slot numbers: `tools/build.py` `check_slots` fails the build if an `fc_slot_*` is not above every native `slot_*`.

Still open in game: a client's view before it has a party; the leave path; the world save and `--load-game`.

## Needed before M0

- TaleWorlds Mount&Blade Warband Module System (1.171 or the latest official), from taleworlds.com.
- WSE2 (the version matching Warband 1.174) from the author's official release.
