# Test launchers

`tools/install.py` copies these into the root of a test copy of the game.

- `fc_server.bat`: starts WSE2's dedicated campaign server with our module, `fc_server.txt` (server name, up to
  16 players, port 7240) and `fc_server_config.ini` (its own log: `rgl_log_server.txt`, so it doesn't share the
  client's `rgl_log.txt`). `--save-no 0 --load-game`: continues the world in save slot 0 (`sg00.sav`, most likely
  `Documents\Mount&Blade Warband WSE2\CampaignCoop\Savegames`) if it exists, else starts a new one. The server
  saves there when a player leaves and once a game day.
- `fc_server_new.bat`: the same with a new world (its first save overwrites `sg00.sav`).
- Server console commands (ours): `fc_save` saves the world now; `fc_characters` lists the characters, whose they
  are and who is connected.
- `fc_client.bat`: starts a game client with our module. In the game: **Multiplayer**, then WSE2's **Join a
  Campaign** button on the profile screen (shown because the module ships `module_config_template.ini` with
  `bHasMultiplayerCampaign=true`; see `docs/wse2-join.md`). It loads the campaign data, then opens the server list
  in campaign mode: pick **Local Area Network** (or Favorites) and join `CampaignCoop_test`.
- `fc_join.bat`: starts a client that connects straight to the campaign server on this PC
  (`--address 127.0.0.1:7240 --campaign`): it loads the campaign data, asks that address directly and joins when
  it answers. Needs an existing multiplayer profile (otherwise the profile screen opens first). Edit the address for
  another PC.
- `fc_server.txt`: server names can't contain spaces; `set_max_players` takes two numbers (players, private
  players).

Two clients on one PC: no. The WSE2 client (32 and 64 bit) creates the mutex "WSE2 Mutex" at start and quits at
once if it exists (WinMain), so a second client on the same Windows session never opens. Test the second player
from another PC (or a VM / another logged-in Windows user: the mutex is per session).
