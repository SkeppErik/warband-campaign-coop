# Warband Campaign Co-op constants. The build appends "from fc_constants import *" to module_constants.py, so
# everything here is visible to the whole module. Keep this file free of imports from module files.

# Player pool: one troop (trp_fc_player_N) and one party (p_fc_player_party_N) per character. A character is bound
# to a player's unique id the first time they join and stays theirs (rejoining gives it back, the world save keeps
# it), so fc_max_players is also the number of different people a world can have.
fc_max_players = 16

# Our slot numbers sit above all of native's (native goes up to 500 in 1.171); the build checks it.
fc_slot_troop_owner = 900   # player_no + 1 of the player connected with this pool troop now, 0 = nobody
fc_slot_troop_bound = 901   # 1 = this pool troop is somebody's character (fc_slot_troop_uid says whose)
fc_slot_troop_uid = 902     # that player's unique id (player_get_unique_id)
fc_slot_troop_menu = 903    # menu_no + 1 of the menu the player sees (server, docs/encounters.md), 0 = none
fc_slot_troop_screen_kind = 904    # trade/loot screen session of this player (fc_items): 1 trade, 2 loot, 0 none
fc_slot_troop_screen_troop = 905   # the other troop of that session
fc_slot_troop_session = 906        # on a merchant/loot troop: pool slot + 1 of the player trading with it
fc_slot_ctx_base = 1000     # 1000 + i: the player's copy of menu global i (and trp_player's: the world's copy)

# Battles: how close (map distance) another player must be to the fight to be offered to join it.
# Unlimited while testing; a native-like value comes later.
fc_join_distance = 1000000

# Network messages (docs/protocol.md). Native uses multiplayer event ids up to 124 and the engine likely caps them at
# 127, so all of ours share one event id; the first value says which message it is, up to three values follow.
fc_event = 125
fc_msg_your_party = 1   # server -> client: (party): this is your party on the map
fc_msg_menu_open = 2    # server -> client: (menu_no, mesh or -1): a menu follows
fc_msg_menu_field = 3   # server -> client: (field): text pieces that follow go to the menu text (-1) or option k
fc_msg_menu_show = 4    # server -> client: (menu_no): show it
fc_msg_menu_close = 5   # server -> client: back to the map
fc_msg_notice = 6       # server -> client: (code): a message to show
fc_msg_menu_choice = 7  # client -> server: (menu_no, option k)
fc_msg_inv_begin = 8    # both ways: (side, troop, gold): an inventory follows (side 0 = the player's troop, 1 = other)
fc_msg_inv_slot = 9     # both ways: (side*1000 + slot, item, modifier*10000 + amount)
fc_msg_inv_end = 10     # both ways: (side)
fc_msg_price = 11       # server -> client: (item, buy factor, sell factor)
fc_msg_screen_open = 12 # server -> client: (kind 1 trade / 2 loot, troop)
fc_msg_screen_done = 13 # client -> server: (kind): back from the screen, both inventories were sent
fc_msg_inv_update = 14  # client -> server: our inventory (just sent) after an item window
fc_items_max_slots = 120    # inventory slots that travel (equipment 0-9 and the bag)
fc_event_text = 126     # string messages (text pieces of up to 250 characters, s0 on the client)
fc_event_message = 127  # string message: show it (display_message of native code running for that player)
fc_notice_unavailable = 1   # "not available in co-op yet"
fc_notice_busy = 2          # "someone else is trading with them"
fc_notice_rejected = 3      # the trade did not add up: undone
