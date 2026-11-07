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

# Battles: how close (map distance) another player must be to the fight to be offered to join it.
# Unlimited while testing; a native-like value comes later.
fc_join_distance = 1000000

# Network messages (docs/protocol.md). Native uses multiplayer event ids up to 124 and the engine likely caps them at
# 127, so all of ours share one event id; the first value says which message it is, up to three values follow.
fc_event = 125
fc_msg_your_party = 1   # server -> client: (party): this is your party on the map
