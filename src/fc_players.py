"""Players on the shared map (M1): every connected player gets a troop and a party from our pool, and their client's
map camera follows that party.

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
    # Input: player_no. Gives the player their character: the pool slot bound to their unique id (a returning
    # player gets the same troop and party back, as the world save left them), or else a slot nobody owns yet
    # (a new character: fresh party near a town).
    ("fc_player_joined", [
        (store_script_param, ":player_no", 1),
        (str_store_player_username, s0, ":player_no"),
        (player_get_unique_id, ":uid", ":player_no"),
        (assign, ":slot", -1),
        (assign, ":new", 0),
        (try_for_range, ":i", 0, fc_max_players),
            (eq, ":slot", -1),
            (store_add, ":troop", "trp_fc_player_0", ":i"),
            (troop_slot_eq, ":troop", fc_slot_troop_bound, 1),
            (troop_slot_eq, ":troop", fc_slot_troop_uid, ":uid"),
            (assign, ":slot", ":i"),
        (try_end),
        (try_for_range, ":i", 0, fc_max_players),
            (eq, ":slot", -1),
            (store_add, ":troop", "trp_fc_player_0", ":i"),
            (troop_slot_eq, ":troop", fc_slot_troop_bound, 0),
            (assign, ":slot", ":i"),
            (assign, ":new", 1),
        (try_end),
        # the same id connected twice (the character is in use by another connection that is still here)
        (assign, ":in_use", 0),
        (try_begin),
            (neq, ":slot", -1),
            (store_add, ":troop", "trp_fc_player_0", ":slot"),
            (troop_get_slot, ":owner", ":troop", fc_slot_troop_owner),
            (gt, ":owner", 0),
            (store_sub, ":owner_no", ":owner", 1),
            (neq, ":owner_no", ":player_no"),
            (player_is_active, ":owner_no"),
            (player_get_unique_id, ":owner_uid", ":owner_no"),
            (eq, ":owner_uid", ":uid"),
            (assign, ":in_use", 1),
        (try_end),
        (try_begin),
            (eq, ":slot", -1),
            (display_message, "@[fc] no free character for {s0}: all pool characters belong to other players"),
        (else_try),
            (eq, ":in_use", 1),
            (display_message, "@[fc] {s0} is already connected with this id: not given a party"),
        (else_try),
            (store_add, ":troop", "trp_fc_player_0", ":slot"),
            (store_add, ":party", "p_fc_player_party_0", ":slot"),
            (store_add, ":owner", ":player_no", 1),
            (troop_set_slot, ":troop", fc_slot_troop_owner, ":owner"),
            (troop_set_name, ":troop", s0),
            (party_set_name, ":party", s0),
            # Build the party BEFORE giving it to the player. WSE2's campaign server (party_clear handler,
            # docs/wse2-join.md): on a player-controlled party party_clear keeps one stack slot (setNumStacks(1)),
            # so clear + add_leader on an empty player party left an uninitialised stack 1 and the server
            # crashed in mbParty::getSkill. Every party is a bot here: parties start as bots, a disconnect makes
            # them bots again, and a loaded world has only bots (the controller is not in the save).
            (try_begin),
                (eq, ":new", 1),
                (troop_set_slot, ":troop", fc_slot_troop_bound, 1),
                (troop_set_slot, ":troop", fc_slot_troop_uid, ":uid"),
                (party_clear, ":party"),
                (party_add_leader, ":party", ":troop"),
                (party_relocate_near_party, ":party", "p_town_1", 2),
            (else_try),
                # returning: keep the party as it is, only make sure its leader is there
                (party_count_members_of_type, ":n", ":party", ":troop"),
                (eq, ":n", 0),
                (party_add_leader, ":party", ":troop"),
            (try_end),
            (enable_party, ":party"),
            (player_set_troop_id, ":player_no", ":troop"),
            (player_set_party_id, ":player_no", ":party"),
            (multiplayer_send_2_int_to_player, ":player_no", fc_event, fc_msg_your_party, ":party"),
            (call_script, "script_fc_send_inventory", ":player_no", 0, ":troop"),
            (assign, reg0, ":player_no"),
            (assign, reg1, ":slot"),
            (assign, reg2, ":new"),
            (display_message, "@[fc] {s0} joined: player {reg0}, character {reg1}{reg2? (new):, returning}"),
        (try_end),
    ]),

    # Client, fc_msg_your_party. Input: party. The map camera follows the player's own party.
    ("fc_client_set_own_party", [
        (store_script_param, ":party", 1),
        (assign, "$fc_my_party", ":party"),
        (set_camera_follow_party, ":party", 1),
        (str_store_party_name, s0, ":party"),
        (display_message, "@[fc] your party: {s0}"),
    ]),

    # Input: player_no. Takes the player's party off the map (it keeps its place, troops and the bond to the
    # player's id, so rejoining brings it back) and saves the world.
    ("fc_player_left", [
        (store_script_param, ":player_no", 1),
        (store_add, ":owner", ":player_no", 1),
        (try_for_range, ":i", 0, fc_max_players),
            (store_add, ":troop", "trp_fc_player_0", ":i"),
            (troop_slot_eq, ":troop", fc_slot_troop_owner, ":owner"),
            (troop_set_slot, ":troop", fc_slot_troop_owner, 0),
            (troop_set_slot, ":troop", fc_slot_troop_menu, 0),
            (store_add, ":party", "p_fc_player_party_0", ":i"),
            (call_script, "script_fc_leave_battle", ":party"),
            (disable_party, ":party"),
            (str_store_troop_name, s0, ":troop"),
            (assign, reg1, ":i"),
            (display_message, "@[fc] {s0} left: character {reg1} put away"),
        (try_end),
        (call_script, "script_fc_save_world"),
    ]),

    # Server: writes the world to the save slot the server was started with (--save-no, sgXY.sav; auto_save =
    # mbGame::save(-1) = that slot). Start the server with --load-game to continue from it.
    ("fc_save_world", [
        (try_begin),
            (multiplayer_is_server),
            (multiplayer_is_campaign),
            (auto_save),
        (try_end),
    ]),
]

# Native allows these two only in mission templates. WSE2's campaign server fires both as simple triggers with the
# player in trigger parameter 1: joined seen in game 2026-11-07; exit read in mbnetNetworkServer::disconnectPlayer
# (runs before the engine resets the player and turns the party back into a bot).
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
    # once a game day
    (24, [
        (call_script, "script_fc_save_world"),
    ]),
]

patches = [
    fp.add_from("troops", _pool_troops, origin="fc_players"),
    fp.add_from("parties", _pool_parties, origin="fc_players"),
    fp.add("scripts", scripts, origin="fc_players"),
    fp.add("simple_triggers", simple_triggers, origin="fc_players"),
]
