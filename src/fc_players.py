"""Players on the shared map (M1): every connected player gets a troop and a party from our pool.

The pool troops and parties are copies of native's own player troop and main party, so they start with native's
look, flags and faction. A pool party starts empty and disabled; joining puts the player's troop in it as leader
and brings it onto the map near a town.
"""
from header_common import *
from header_operations import *
from header_triggers import *
from header_parties import *
from module_constants import *
import fcpatch as fp


def _native(entries, id, what):
    found = [e for e in entries if fp.entry_id(e) == id]
    if len(found) != 1:
        raise fp.PatchError("fc_players: native %s %r not found" % (what, id))
    return found[0]


def _pool_troops(troops):
    base = _native(troops, "player", "troop")
    # same type as native's entry: process_troops.py edits troops in place, so they must be lists
    return [type(base)(["fc_player_%d" % i, "Player", "Players"] + list(base[3:])) for i in range(fc_max_players)]


def _pool_parties(parties):
    native = _native(parties, "main_party", "party")
    base = list(native)
    out = []
    for i in range(fc_max_players):
        p = list(base)
        p[0] = "fc_player_party_%d" % i
        p[1] = "Player"
        p[2] = base[2] | pf_disabled
        p[10] = []   # members: the player's troop is added on join
        out.append(type(native)(p))
    return out


scripts = [
    # Input: player_no. Gives the player a free pool troop and party and puts the party on the map.
    ("fc_player_joined", [
        (store_script_param, ":player_no", 1),
        (str_store_player_username, s0, ":player_no"),
        (assign, ":slot", -1),
        (try_for_range, ":i", 0, fc_max_players),
            (eq, ":slot", -1),
            (store_add, ":troop", "trp_fc_player_0", ":i"),
            (troop_get_slot, ":owner", ":troop", fc_slot_troop_owner),
            (assign, ":free", 1),
            (try_begin),
                (gt, ":owner", 0),
                (store_sub, ":owner_no", ":owner", 1),
                (player_is_active, ":owner_no"),
                (neq, ":owner_no", ":player_no"),
                (assign, ":free", 0),
            (try_end),
            (eq, ":free", 1),
            (assign, ":slot", ":i"),
        (try_end),
        (try_begin),
            (eq, ":slot", -1),
            (display_message, "@[fc] no free player slot for {s0}"),
        (else_try),
            (store_add, ":troop", "trp_fc_player_0", ":slot"),
            (store_add, ":party", "p_fc_player_party_0", ":slot"),
            (store_add, ":owner", ":player_no", 1),
            (troop_set_slot, ":troop", fc_slot_troop_owner, ":owner"),
            (troop_set_name, ":troop", s0),
            (party_set_name, ":party", s0),
            (player_set_troop_id, ":player_no", ":troop"),
            (player_set_party_id, ":player_no", ":party"),
            (party_clear, ":party"),
            (party_add_leader, ":party", ":troop"),
            (enable_party, ":party"),
            (party_relocate_near_party, ":party", "p_town_1", 2),
            (assign, reg0, ":player_no"),
            (assign, reg1, ":slot"),
            (display_message, "@[fc] {s0} joined: player {reg0}, slot {reg1}"),
        (try_end),
    ]),

    # Input: player_no. Frees the player's pool slot and takes the party off the map.
    ("fc_player_left", [
        (store_script_param, ":player_no", 1),
        (store_add, ":owner", ":player_no", 1),
        (try_for_range, ":i", 0, fc_max_players),
            (store_add, ":troop", "trp_fc_player_0", ":i"),
            (troop_slot_eq, ":troop", fc_slot_troop_owner, ":owner"),
            (troop_set_slot, ":troop", fc_slot_troop_owner, 0),
            (store_add, ":party", "p_fc_player_party_0", ":i"),
            (disable_party, ":party"),
            (str_store_troop_name, s0, ":troop"),
            (assign, reg1, ":i"),
            (display_message, "@[fc] {s0} left: slot {reg1} free"),
        (try_end),
    ]),
]

# VERIFY at M1: native allows these two only in mission templates; WSE2's campaign server is assumed to fire them
# as simple triggers on the map, with the player in trigger parameter 1.
simple_triggers = [
    (ti_server_player_joined, [
        (multiplayer_is_server),
        (multiplayer_is_campaign),
        (store_trigger_param_1, ":player_no"),
        (call_script, "script_fc_player_joined", ":player_no"),
    ]),
    (ti_on_player_exit, [
        (multiplayer_is_server),
        (multiplayer_is_campaign),
        (store_trigger_param_1, ":player_no"),
        (call_script, "script_fc_player_left", ":player_no"),
    ]),
]

patches = [
    fp.add_from("troops", _pool_troops, origin="fc_players"),
    fp.add_from("parties", _pool_parties, origin="fc_players"),
    fp.add("scripts", scripts, origin="fc_players"),
    fp.add("simple_triggers", simple_triggers, origin="fc_players"),
]
