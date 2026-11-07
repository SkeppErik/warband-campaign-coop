# How a WSE2 client joins a campaign server

Found by reverse engineering `mb_warband_wse2.exe` (official WSE2, exes dated 2026-10-14) in Ghidra with the PDB
that ships next to it (2026-11-07). Function names below are from that PDB.

## The "Join a Campaign" button

- `mbProfileWindow::open` (the multiplayer profile screen: Join a Game / Host a Game / Back) creates
  `join_campaign_button` (text `ui_join_campaign` = "Join a Campaign") only if
  `rglConfig::General::bHasMultiplayerCampaign` is true. Nothing else sets that flag: only `rglConfig::load`
  writes it, from key `bHasMultiplayerCampaign` in section `[General]`.
- `mbCoreGame::loadConfig` (called from `WinMain` after the module path is known):
  1. loads `Documents\Mount&Blade Warband WSE2\rgl_config.ini` (copied from `rgl_config_template.ini` if missing);
  2. copies `Modules\<module>\module_config_template.ini` over `Documents\...\<module>\module_config.ini`
     (overwriting). **If the template is missing it deletes that Documents file**;
  3. loads the Documents `module_config.ini`.
- Later `mbCoreGame::doModuleCommand` (from `mbStartingWindow::doStep`), when `bLoadModuleIniOptions` is true,
  rewrites the Documents `module_config.ini` from module.ini's options and loads it again. `rglIni::getBool`
  returns the current value when a key is missing, so the flag set in step 3 stays on.
- So: the module ships `module_config_template.ini` with `[General] bHasMultiplayerCampaign=true`. A
  `module_config.ini` in the module folder is never read (our first attempt).

## What the button does

`mbProfileWindow::frameMove`: saves profiles, sets `windows[3]` (`mbLoadingWindow`) to mode 6 and opens it.
Mode 6 sets `g_basicGame.m_gameType = 4` (campaign client), creates the game, reads the settings data and the map,
starts the game as multiplayer and initializes the meta mission. Afterwards, if a profile exists, it opens
`windows[0x1a]` (`mbMultiplayerClientWindow`, the normal server list: Internet / Local Area Network / Favorites);
otherwise the profile screen. Connecting with `m_gameType == 4` puts the client on the map window (`windows[6]`)
after the server's mission info.

## Launch options `--address host:port --campaign`

- `WinMain` stores the address (`m_storedAddress`), sets `m_switchingModule`, and `m_switchingToCampaign` when
  `--campaign` is on the command line.
- `mbStartingWindow` then opens `mbLoadingWindow` in mode 6 (campaign) instead of 4.
- `mbMultiplayerClientWindow::open` with `m_switchingModule` uses search type 4: `ServerSearchThread` asks that
  one address directly (port defaults to `rglConfig::Network::iServerPort`). `frameMove` connects by itself once
  the list holds exactly that one server.
- Search types: 0 internet (main server), 1 LAN, 2 the profile's favorites, 3 (another list), 4 stored address.

## Server side

`mbnetNetworkServer::receiveEvent` answers a client of the wrong kind with `ui_server_for_wse2_campaign`
("This server is for an online campaign on WSE2, please launch WSE2 and select Join a Campaign").

## Player parties on the campaign server (mb_warband_wse2_dedicated_campaign.exe, its PDB)

- `mbParty::initialize` makes every party a bot (`m_controller` at +0x5700 = 1). `player_set_party_id`
  (`mbGame::playerSetParty`) sets the party's player (+0x56fc) and `m_controller` = 0 (2 on the player's own
  machine); the player's previous party goes back to bot. `mbnetNetworkServer::disconnectPlayer` sets it to 1.
  The server sends the change to clients (`fillPlayerPartyClientEvent`); a client whose own player it is sets
  `g_game->m_mainPartyNo` to that party.
- `party_clear`: on the main party or a non-bot party it calls `setNumStacks(1)` (keeps a leader slot), else
  `setNumStacks(0)`. On an empty player party that leaves stack 0 uninitialised; `party_add_leader` then shifts it
  to stack 1 and `mbParty::getSkill` (from `calculateSpeed`) reads a garbage troop id: server crash
  (seen 2026-11-07). So: build a party (clear, add leader) before `player_set_party_id`.
- `party_add_leader` refuses the main party, adds `max(count, 1)`.
- `ti_server_player_joined` fires on the campaign server as a simple trigger, player in trigger parameter 1.

## World saves on the campaign server

- `--save-no N` (0..99, default 0) sets the save slot; `--load-game` loads `sg<N/10><N%10>.sav` at start if it reads
  as a valid save (magic, game version, module version), else the server starts a new world (`mbGame::start`).
  The file is under My Documents (`mbBasicGame::getMyDocumentsSavegamePath`: Documents\<app folder>\<module>\...).
- The native operation `auto_save` calls `mbGame::save(-1)`, which writes the slot in `g_game->m_savegameNo` (the
  `--save-no` slot) through `new_game.sav`, keeping `last_savegame_backup.sav`.
- A party's controller (+0x5700) is not read from the save (only `initialize`, `playerSetParty`,
  `disconnectPlayer` write it), so every party of a loaded world is a bot until `player_set_party_id`.
- On disconnect the server runs the `ti_on_player_exit` simple triggers first, then turns the player's party back
  into a bot and clears the player's party.

## Network messages and clients

- Client `mbnetNetworkClient::receiveEvent`: script events (multiplayer_send_*_to_player) run mapped script 0x27 =
  `game_receive_network_message` (engine table `g_mappedScripts`; 0x3d = `wse_savegame_loaded`).
- `WinMain` creates the mutex "WSE2 Mutex" and returns at once if it already exists (ERROR_ALREADY_EXISTS): one
  client per Windows session; the x64 client uses the same name.
