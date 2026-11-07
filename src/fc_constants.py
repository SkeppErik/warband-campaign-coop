# Warband Campaign Co-op constants. The build appends "from fc_constants import *" to module_constants.py, so
# everything here is visible to the whole module. Keep this file free of imports from module files.

# Player pool: one troop (trp_fc_player_N) and one party (p_fc_player_party_N) per connected player. Taken on join,
# freed on leave; a slot whose owner is no longer connected counts as free (a loaded world keeps stale owners).
fc_max_players = 16

# Our slot numbers sit above all of native's (native goes up to 500 in 1.171); the build checks it.
fc_slot_troop_owner = 900   # player_no + 1 of the player using this pool troop, 0 = free

# Battles: how close (map distance) another player must be to the fight to be offered to join it.
# Unlimited while testing; a native-like value comes later.
fc_join_distance = 1000000
