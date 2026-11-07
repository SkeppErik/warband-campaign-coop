# Test launchers

`tools/install.py` copies these into the root of a test copy of the game.

- `fc_server.bat`: starts WSE2's dedicated campaign server with our module, `fc_server.txt` (server name, up to
  16 players, port 7240) and `fc_server_config.ini` (its own log: `rgl_log_server.txt`, so it doesn't share the
  client's `rgl_log.txt`).
- `fc_client.bat`: starts a game client with our module. In the game: **Multiplayer**, then WSE2's **Join
  campaign** button on the profile screen (it needs `bHasMultiplayerCampaign=true` in the module's
  `module_config.ini`, which the install adds). Fallback: **Start a new game**, then **Join the co-op campaign on
  this PC**.
- `fc_join.bat`: starts a client that connects straight to the campaign server on this PC, with WSE2's launch
  options `--address 127.0.0.1:7240 --campaign` (found in the WSE2 executable; edit the address for another PC).
- `fc_server.txt`: server names can't contain spaces; `set_max_players` takes two numbers (players, private
  players).

Not confirmed yet (first in-game check): whether the campaign server needs anything beyond these commands to start
its world, and whether two clients can run on one PC (Warband normally allows only one).
