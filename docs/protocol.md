# Network protocol

Every message between the campaign server and a client goes over **one multiplayer event id, `fc_event` = 125**
(`src/fc_constants.py`). Native uses event ids up to 124, and the engine likely caps them at 127, so we don't take
more than one.

A message is up to four integers: the **message type** first, then up to three values:

```
(multiplayer_send_4_int_to_player, <player>, fc_event, <message type>, <value 1>, <value 2>, <value 3>)
(multiplayer_send_4_int_to_server, fc_event, <message type>, <value 1>, <value 2>, <value 3>)
```

Fewer values use the 2- or 3-int forms. Both sides receive in native's `game_receive_network_message`, whose start
hands `fc_event` to `script_fc_net_received` (`src/fc_net.py`); native's own events pass through untouched.

Rules:
- The server checks every client message: the sender must be allowed to ask for it (it's their party, they are
  near, they are not busy), and every id in it must be in range. A client message is a request, never a fact.
- Ids of parties, troops and items are native's ids. Players are identified by player number only within one
  connection; anything kept longer is keyed by the player's Steam id (M2).
- Message types are never reused for something else; a retired type stays listed as retired.

WSE2's composite messages (strings, positions, any number of values) need `bBreakWarbandCompatibility` on every
machine. They are not used yet; if a message ever needs more than three integers, decide then.

## Messages

| Type | Name | Direction | Values | Meaning |
|---|---|---|---|---|
| 1 | `fc_msg_your_party` | server -> client | party | This is your party on the map; the camera follows it. Sent on joining. |
