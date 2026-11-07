# Test launchers

`tools/install.py` copies these into the root of a test copy of the game.

- `fc_server.bat`: starts WSE2's dedicated campaign server with our module and `fc_server.txt` (server name, up
  to 16 players, port 7240).
- `fc_client.bat`: starts a game client with our module. In the game: Multiplayer, then WSE2's **Join campaign**
  button, address `127.0.0.1:7240` (same PC) or the server PC's address.

Not confirmed yet (first in-game check): whether the campaign server needs anything beyond these commands to start
its world, and whether two clients can run on one PC (Warband normally allows only one).
