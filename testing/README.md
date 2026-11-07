# Test launchers

`tools/install.py` copies these into the root of a test copy of the game.

- `fc_server.bat`: starts WSE2's dedicated campaign server with our module, `fc_server.txt` (server name, up to
  16 players, port 7240) and `fc_server_config.ini` (its own log: `rgl_log_server.txt`, so it doesn't share the
  client's `rgl_log.txt`).
- `fc_client.bat`: starts a game client with our module. In the game: **Start a new game**, then **Join the co-op
  campaign on this PC** (WSE2's own "Join campaign" button did not appear on the multiplayer screen).

Not confirmed yet (first in-game check): whether the campaign server needs anything beyond these commands to start
its world, and whether two clients can run on one PC (Warband normally allows only one).
