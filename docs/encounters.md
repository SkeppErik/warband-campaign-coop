# Encounters and menus (M3)

## What the engine gives us (WSE2 campaign server, reverse engineered 2026-11-07)

- `mbGame::startEncounter(mover, target)` on the server (game type 5):
  - AI party meets AI party: `startBattle` (a map event) that the server simulates.
  - AI party attacks a player's party, or a player's party reaches a party, town, village or a battle: a map event
    with both parties (`startBattle`: both get behaviour 7 = in an event, frozen), then native
    `game_event_party_encounter(encountered, encountered_2, player_party)`: **parameter 3 is the player's party**.
- `mbEvent::frameMove` simulates every battle event that doesn't contain the server's main party
  (native `game_event_simulate_battle`), so player parties' events were simulated too (the stun lock).
- A campaign client never runs `game_event_party_encounter` (only game type 5 does).
- The engine sends clients only world data: parties (spawn, stacks, flags, faction, name), map events, the date, a
  player's party / troop / gold. No menus, no slots, no global variables, no troop data, no merchant stock.
  Client -> server: party control (moving), teleport, "player in menu", chat, script messages.
- Script messages: ints (`multiplayer_send_3_int_to_*`) and strings (`multiplayer_send_string_to_player`, at
  most 300 characters, arrives in s0 with the message type as parameter 2).
- Ending an encounter for one party: `party_leave_cur_battle` (party parameter); `leave_encounter` works on the
  engine's main party only.

## Design: menus run on the server, the client shows them

The client's copy of the world has no script state (game_start never ran there; slots and globals aren't
mirrored), so native menus can't run on the client. They run on the server, for one player at a time:

1. **Context.** At build time every native script, menu, trigger and simple trigger gets `p_main_party` ->
   `$fc_main_party` and `trp_player` -> `$fc_player_troop`. Both globals are 0 by default (= `p_main_party`,
   `trp_player`), so single player and the server's own world triggers behave exactly as before.
   `script_fc_ctx_enter(player)` points them at the player's party and troop (and `set_player_troop`) and swaps in
   the player's copy of the menu globals; `script_fc_ctx_leave` swaps back.
   Menu globals = the globals that native's menus and `game_event_party_encounter` write and that no trigger
   writes (computed by the build, listed in the build output); each player keeps their own copy in pool troop slots.
2. **Menu ops.** The operations that change menus or open screens are replaced by calls to `script_fc_op_*`:
   outside a context they run the native operation (single player and clients unchanged); in a context they record
   the request: `jump_to_menu` -> next menu, `change_screen_return`/`_map`/`_quit` -> close, `leave_encounter` ->
   `party_leave_cur_battle` on the player's party, `set_background_mesh` -> the menu picture; missions, trade, loot,
   conversations, waiting and presentations -> "not available in co-op yet" (they come in later milestones).
3. **Menus as scripts.** For every native menu the build makes scripts from its blocks: its ops, each option's
   conditions (ending with `$fc_ok = 1`, so a failed condition hides the option exactly as native) and each
   option's consequences.
4. **Encounter.** Ops at the start of `game_event_party_encounter`: on the campaign server, with parameter 3 a
   pool party, run the native script in that player's context, then show the player the menu it chose.
5. **Showing a menu.** The server runs the menu's ops (following jumps), evaluates its text and the options whose
   conditions pass, and sends them (texts in 250-character pieces). The client keeps them in a WSE2 dictionary and
   opens `mnu_fc_remote`, a native game menu whose text and options are filled from it. Choosing an option sends
   (menu, option) to the server, which runs that option's consequences in the player's context and sends the next
   menu, or closes it (the party leaves the encounter).
6. **Battles.** Until M4 the server never simulates a battle event that includes a player's party
   (`game_event_simulate_battle` ends it); AI parties still don't target player parties.

## Items: trade, loot and the player's inventory (`src/fc_items.py`)

- The engine never sends troop inventories or troop gold (only the multiplayer `player_set_gold`), so we do.
- `change_screen_trade` / `change_screen_loot` in a player's context start a screen session: the server sends both
  inventories and (trade) the price factors of every item involved, computed by native's price scripts for that
  player; the client fills its copies of the troops, keeps the factors (its price scripts return them) and opens
  the native screen. Back in the menu (or on the map), the client sends both inventories; the server accepts them
  if every item kind's count over both troops and the gold sum are unchanged, runs native's buy/sell events for
  what changed hands (town prices), and shows the menu again. One player per merchant at a time.
- Own inventory: after an inventory/party/character window (`wse_window_opened`) the client sends its inventory
  from the map; the server accepts rearranging and dropping only (no new items, same gold), else sends its own.
- The server sends the player's inventory on join and after each menu choice (menus change gold and items).
- Received inventories wait in a WSE2 dictionary (buffer troops would change the troop list and break saves).
- Deviations: prices don't rise while you buy within one visit (they change when the trade is done); the server
  checks that nothing is created, not that the client paid native's price.

## Not yet (later milestones)

Missions (walking in towns, battles, sieges), conversations (and the trades they open), waiting/resting,
presentations started from menus. Each says "not available in co-op yet" and keeps the player in the menu.
