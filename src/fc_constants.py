# Warband Campaign Co-op constants. The build appends "from fc_constants import *" to module_constants.py, so
# everything here is visible to the whole module. Keep this file free of imports from module files.

# Player pool: one troop (trp_fc_player_N) and one party (p_fc_player_party_N) per connected player. Taken on join,
# freed on leave; a slot whose owner is no longer connected counts as free (a loaded world keeps stale owners).
fc_max_players = 16

# Our slot numbers sit far above native's. The build will check them against native's slot constants (to do).
fc_slot_troop_owner = 900   # player_no + 1 of the player using this pool troop, 0 = free
