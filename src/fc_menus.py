"""Native menus on the campaign server, shown on the client (M3, docs/encounters.md).

Build time:
- every native script, menu, trigger and simple trigger: p_main_party -> $fc_main_party, trp_player ->
  $fc_player_troop (0 by default = native), and the menu/screen operations -> script_fc_op_* (native outside a
  player context; recorded inside one);
- scripts made from every native menu (fc_mo_N ops, fc_mc_N_K conditions, fc_mx_N_K consequences, fc_mr_N text
  and options, fc_mk_N choice);
- context switching (script_fc_ctx_enter / _leave) with each player's copy of the menu globals.
"""
import os
import re

from header_common import *
from header_operations import *
from header_game_menus import *
from module_constants import *
import fcpatch as fp
import fc_rewrite as rw

# ---------------------------------------------------------------- operations that change menus or open screens

# opcode name -> what it does inside a player's context
CTX_JUMP = "jump"
CTX_CLOSE = "close"
CTX_LEAVE = "leave"
CTX_MESH = "mesh"
CTX_NOTHING = "nothing"
CTX_UNAVAILABLE = "unavailable"
CTX_MESSAGE = "message"
CTX_TRADE = "trade"
CTX_LOOT = "loot"
CTX_TALK_START = "talk_start"            # change_screen_map_conversation: dialog state "start"
CTX_TALK_EVENT = "talk_event"            # start_map_conversation: dialog state "event_triggered"

_ops = dict((k, v) for k, v in globals().items() if isinstance(v, int) and k.islower() and not k.startswith("_"))
_change_screens = sorted(k for k in _ops if k.startswith("change_screen_"))

CTX_OPS = {"display_message": CTX_MESSAGE, "display_log_message": CTX_MESSAGE, "jump_to_menu": CTX_JUMP, "leave_encounter": CTX_LEAVE, "set_background_mesh": CTX_MESH,
           "set_party_battle_mode": CTX_NOTHING, "finish_party_battle_mode": CTX_NOTHING,
           "end_current_battle": CTX_NOTHING,
           "rest_for_hours": CTX_UNAVAILABLE,
           "rest_for_hours_interactive": CTX_UNAVAILABLE, "start_presentation": CTX_UNAVAILABLE}
for _name in _change_screens:
    CTX_OPS[_name] = CTX_CLOSE if _name in ("change_screen_return", "change_screen_map", "change_screen_quit") \
        else CTX_UNAVAILABLE
CTX_OPS["change_screen_trade"] = CTX_TRADE   # fc_items: screen sessions
CTX_OPS["change_screen_loot"] = CTX_LOOT
CTX_OPS["change_screen_map_conversation"] = CTX_TALK_START   # fc_dialogs
CTX_OPS["start_map_conversation"] = CTX_TALK_EVENT
CTX_OPS = dict((k, v) for k, v in CTX_OPS.items() if k in _ops)

MAX_OP_ARGS = 4   # every (operation, 0..4 arguments) gets a script: each list compiles in its own process, so the
                  # scripts can't depend on what another list's rewrite needed


def _op_script(name):
    def make(nargs):
        if nargs > MAX_OP_ARGS:
            raise fp.PatchError("fc_menus: %s with %d arguments" % (name, nargs))
        return "script_fc_op_%s_%d" % (name, nargs)
    return make


REPLACE = dict((_ops[name], _op_script(name)) for name in CTX_OPS)
RENAME = {"p_main_party": "$fc_main_party", "trp_player": "$fc_player_troop"}

# operations that write a destination: inside a player's context they read our per-player value instead
CTX_DESTINATIONS = {
    "store_conversation_troop": "$fc_talk_troop",
    "store_conversation_agent": -1,
    "store_repeat_object": "$fc_repeat_object",
    "store_encountered_party": "$g_encountered_party",
    "store_encountered_party2": "$g_encountered_party_2",
}


def _expand(name, value):
    def make(args):
        return [
            (try_begin),
                (gt, "$fc_ctx_player", 0),
                (assign, args[0], value),
            (else_try),
                (_ops[name],) + tuple(args),
            (try_end),
        ]
    return make


EXPAND = dict((_ops[n], _expand(n, v)) for n, v in CTX_DESTINATIONS.items() if n in _ops)


def rewrite(block):
    return rw.rewrite_block(block, REPLACE, RENAME, call_script, EXPAND)


def _rewrite_script(e):
    return (e[0], rewrite(e[1])) + tuple(e[2:])


def _rewrite_simple_trigger(e):
    return (e[0], rewrite(e[1])) + tuple(e[2:])


def _rewrite_trigger(e):
    return tuple(e[:3]) + (rewrite(e[3]), rewrite(e[4])) + tuple(e[5:])


def _rewrite_option(o):
    o = list(o)
    o[1] = rewrite(o[1])
    o[3] = rewrite(o[3])
    return tuple(o)


def _rewrite_menu(m):
    m = list(m)
    m[4] = rewrite(m[4])
    m[5] = [_rewrite_option(o) for o in m[5]]
    return tuple(m)


def _op_scripts():
    """One script per (operation, number of arguments) the rewritten code calls."""
    out = []
    for (name, n) in sorted((name, n) for name in CTX_OPS for n in range(MAX_OP_ARGS + 1)):
        params = [(store_script_param, ":p%d" % (i + 1), i + 1) for i in range(n)]
        args = tuple(":p%d" % (i + 1) for i in range(n))
        kind = CTX_OPS[name]
        if kind in (CTX_JUMP, CTX_MESH) and n == 0:
            inside = []
        elif kind == CTX_JUMP:
            inside = [(store_add, "$fc_next_menu", ":p1", 1)]
        elif kind == CTX_CLOSE:
            inside = [(assign, "$fc_menu_close", 1)]
        elif kind == CTX_LEAVE:
            inside = [(call_script, "script_fc_leave_battle", "$fc_main_party")]
        elif kind == CTX_MESH:
            inside = [(assign, "$fc_menu_mesh", ":p1")]
        elif kind == CTX_MESSAGE and n >= 1:
            # the player sees it (the text is filled in now, with the registers native code set)
            inside = [
                (str_store_string, s67, ":p1"),
                (store_sub, ":player", "$fc_ctx_player", 1),
                (str_length, ":len", s67),
                (val_min, ":len", 299),
                (str_store_substring, s66, s67, 0, ":len"),
                (multiplayer_send_string_to_player, ":player", fc_event_message, s66),
            ]
        elif kind in (CTX_TRADE, CTX_LOOT) and n >= 1:
            inside = [(assign, "$fc_screen_kind", 1 if kind == CTX_TRADE else 2), (assign, "$fc_screen_troop", ":p1")]
        elif kind in (CTX_TALK_START, CTX_TALK_EVENT) and n >= 1:
            import fc_dialogs
            state = fc_dialogs.state_ids()["start" if kind == CTX_TALK_START else "event_triggered"]
            inside = [(store_add, "$fc_talk_request", ":p1", 1), (assign, "$fc_talk_state", state)]
        elif kind in (CTX_NOTHING, CTX_MESSAGE, CTX_TALK_START, CTX_TALK_EVENT):
            inside = []
        else:
            inside = [(assign, "$fc_unavailable", 1)]
        native = (_ops[name],) + args if args else _ops[name]
        out.append(("fc_op_%s_%d" % (name, n), params + [
            (try_begin),
                (gt, "$fc_ctx_player", 0),
            ] + inside + [
            (else_try),
                native,
            (try_end),
        ]))
    return out


# ---------------------------------------------------------------- menus as scripts

MAX_SHOWN_OPTIONS = 24   # client: s41..s64


def _native_menus():
    from fcnative_module_game_menus import game_menus
    return game_menus


def _menu_scripts(menus):
    mo, mc, mx, mr, mk = [], [], [], [], []
    for i, m in enumerate(menus):
        mesh = -1 if m[3] in ("none", "", None, 0) else ("mesh_" + m[3] if isinstance(m[3], str) else m[3])
        mo.append(("fc_mo_%d" % i, [(assign, "$fc_menu_mesh", mesh)] + rewrite(m[4])))
        render = [
            (store_script_param, ":player", 1),
            (str_store_string, s67, "@" + m[2]),
            (call_script, "script_fc_send_field", ":player", -1),
        ]
        choose = [(store_script_param, ":k", 1)]
        for k, o in enumerate(m[5]):
            mc.append(("cf_fc_mc_%d_%d" % (i, k), rewrite(o[1]) + [(assign, "$fc_ok", 1)]))
            mx.append(("cf_fc_mx_%d_%d" % (i, k), rewrite(o[3])))
            render += [
                (assign, "$fc_ok", 0),
                (try_begin),
                    (call_script, "script_cf_fc_mc_%d_%d" % (i, k)),
                (try_end),
                (try_begin),
                    (eq, "$fc_ok", 1),
                    (str_store_string, s67, "@" + o[2]),
                    (call_script, "script_fc_send_field", ":player", k),
                (try_end),
            ]
            choose += [
                (try_begin),
                    (eq, ":k", k),
                    (assign, "$fc_ok", 0),
                    (try_begin),
                        (call_script, "script_cf_fc_mc_%d_%d" % (i, k)),
                    (try_end),
                    (eq, "$fc_ok", 1),
                    (try_begin),
                        (call_script, "script_cf_fc_mx_%d_%d" % (i, k)),
                    (try_end),
                (try_end),
            ]
        mr.append(("fc_mr_%d" % i, render))
        mk.append(("fc_mk_%d" % i, choose))
    # each kind in one run, so "script_fc_mo_0" + menu_no is the menu's script
    return mo + mr + mk + mc + mx


# ---------------------------------------------------------------- per-player copies of the menu globals

def _destination_ops():
    """Opcodes whose first argument is written: assign, val_*, and every "<destination>" operation."""
    import header_operations
    path = os.path.splitext(header_operations.__file__)[0] + ".py"
    with open(path) as f:
        text = f.read()
    names = set(re.findall(r"^(\w+)\s*=\s*\d+\s*#\s*\(\s*\w+\s*,\s*<destination", text, re.M))
    names |= set(k for k in _ops if k.startswith("val_") or k == "assign" or k.startswith("store_"))
    return set(_ops[n] for n in names if n in _ops)


def _all_blocks_of_menus(menus):
    for m in menus:
        yield m[4]
        for o in m[5]:
            yield o[1]
            yield o[3]


def menu_globals():
    from fcnative_module_scripts import scripts
    from fcnative_module_simple_triggers import simple_triggers
    from fcnative_module_triggers import triggers
    dest = _destination_ops()
    written = []
    blocks = list(_all_blocks_of_menus(_native_menus()))
    blocks += [s[1] for s in scripts if s[0] == "game_event_party_encounter"]
    for b in blocks:
        for g in rw.written_globals(b, dest):
            if g not in written:
                written.append(g)
    world = set()
    for t in simple_triggers:
        world |= set(rw.written_globals(t[1], dest))
    for t in triggers:
        world |= set(rw.written_globals(t[3], dest)) | set(rw.written_globals(t[4], dest))
    return [g for g in written if g not in world and not g.startswith("fc_")]


# our own globals that must survive between one player's actions (a conversation spans several)
CONTEXT_EXTRAS = ["fc_talk_troop", "fc_talk_party", "fc_repeat_object", "fc_next_menu", "fc_menu_close",
                  "fc_talk_request", "fc_talk_state"]


def _context_scripts():
    names = menu_globals() + CONTEXT_EXTRAS
    with open("fc_menu_globals.txt", "w") as f:   # in the build's src folder, for review
        f.write("\n".join(names) + "\n")
    save_world, load_player, save_player, load_world = [], [], [], []
    for j, g in enumerate(names):
        slot = fc_slot_ctx_base + j
        save_world.append((troop_set_slot, "trp_player", slot, "$" + g))
        load_player.append((troop_get_slot, "$" + g, ":troop", slot))
        save_player.append((troop_set_slot, ":troop", slot, "$" + g))
        load_world.append((troop_get_slot, "$" + g, "trp_player", slot))
    return [
        # Input: player_no. Native code now acts for this player (their party, troop and menu globals).
        ("cf_fc_ctx_enter", [
            (store_script_param, ":player", 1),
            (call_script, "script_fc_pool_slot_of_player", ":player"),
            (assign, ":slot", reg0),
            (ge, ":slot", 0),
            (store_add, ":troop", "trp_fc_player_0", ":slot"),
            (store_add, ":party", "p_fc_player_party_0", ":slot"),
            (store_add, "$fc_ctx_player", ":player", 1),
            (assign, "$fc_main_party", ":party"),
            (assign, "$fc_player_troop", ":troop"),
            (set_player_troop, ":troop"),
        ] + save_world + load_player),
        ("fc_ctx_leave", [
            (try_begin),
                (gt, "$fc_ctx_player", 0),
                (assign, ":troop", "$fc_player_troop"),
            ] + save_player + load_world + [
                (assign, "$fc_ctx_player", 0),
                (assign, "$fc_main_party", "p_main_party"),
                (assign, "$fc_player_troop", "trp_player"),
                (set_player_troop, "trp_player"),
            (try_end),
        ]),
    ]


# ---------------------------------------------------------------- server side

server_scripts = [
    # What one step of native code asked for, cleared before the step (menus: everything; a conversation keeps
    # the menu requests until it ends, see fc_dialogs).
    ("fc_flags_reset", [
        (assign, "$fc_unavailable", 0),
        (assign, "$fc_screen_kind", 0),
    ]),

    # Input: player_no. reg0 = their pool slot (character), -1 if they have none.
    ("fc_pool_slot_of_player", [
        (store_script_param, ":player", 1),
        (store_add, ":owner", ":player", 1),
        (assign, reg0, -1),
        (try_for_range, ":i", 0, fc_max_players),
            (store_add, ":troop", "trp_fc_player_0", ":i"),
            (troop_slot_eq, ":troop", fc_slot_troop_owner, ":owner"),
            (assign, reg0, ":i"),
        (try_end),
    ]),

    # Input: party. Takes it out of its map event (encounter) if it is in one.
    ("fc_leave_battle", [
        (store_script_param, ":party", 1),
        (try_begin),
            (party_get_battle_opponent, ":opponent", ":party"),
            (neq, ":opponent", -1),
            (party_leave_cur_battle, ":party"),
        (try_end),
    ]),

    # Input: player_no, field (-1 = menu text, else the option's index). Sends s67 in 250-character pieces.
    ("fc_send_field", [
        (store_script_param, ":player", 1),
        (store_script_param, ":field", 2),
        (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_menu_field, ":field", 0),
        (str_length, ":len", s67),
        (store_add, ":pieces", ":len", 249),
        (val_div, ":pieces", 250),
        (try_for_range, ":i", 0, ":pieces"),
            (store_mul, ":start", ":i", 250),
            # WSE2's str_store_substring fails (and leaves s66 as it was) if the length runs past the end
            (store_sub, ":piece", ":len", ":start"),
            (val_min, ":piece", 250),
            (str_store_substring, s66, s67, ":start", ":piece"),
            (multiplayer_send_string_to_player, ":player", fc_event_text, s66),
        (try_end),
    ]),

    # In a player's context: runs the player's current menu's ops (following jumps), then sends it, or closes it.
    ("fc_menu_show", [
        (store_script_param, ":player", 1),
        (troop_get_slot, ":menu", "$fc_player_troop", fc_slot_troop_menu),
        (val_sub, ":menu", 1),
        (assign, ":done", 0),
        (try_for_range, ":unused", 0, 10),
            (eq, ":done", 0),
            (ge, ":menu", 0),
            (assign, "$fc_next_menu", 0),
            (assign, "$fc_menu_close", 0),
            (assign, "$fc_unavailable", 0),
            (assign, "$fc_screen_kind", 0),
            (assign, "$fc_talk_request", 0),
            (store_add, ":script", "script_fc_mo_0", ":menu"),
            (try_begin),
                (call_script, ":script"),
            (try_end),
            (try_begin),
                (eq, "$fc_menu_close", 1),
                (assign, ":done", 2),
            (else_try),
                (gt, "$fc_next_menu", 0),
                (store_sub, ":menu", "$fc_next_menu", 1),
            (else_try),
                (assign, ":done", 1),
            (try_end),
        (try_end),
        (try_begin),
            (eq, ":done", 1),
            (gt, "$fc_talk_request", 0),
            # the menu's ops started a conversation (native: the menu shows after it)
            (store_add, ":slot_value", ":menu", 1),
            (troop_set_slot, "$fc_player_troop", fc_slot_troop_menu, ":slot_value"),
            (store_sub, ":troop", "$fc_talk_request", 1),
            (assign, "$fc_talk_request", 0),
            (assign, "$fc_next_menu", 0),
            (assign, "$fc_menu_close", 0),
            (call_script, "script_fc_dialog_begin", ":player", ":troop", "$fc_talk_state"),
        (else_try),
            (eq, ":done", 1),
            (store_add, ":slot_value", ":menu", 1),
            (troop_set_slot, "$fc_player_troop", fc_slot_troop_menu, ":slot_value"),
            (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_menu_open, ":menu", "$fc_menu_mesh"),
            (store_add, ":script", "script_fc_mr_0", ":menu"),
            (try_begin),
                (call_script, ":script", ":player"),
            (try_end),
            (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_menu_show, ":menu", 0),
        (else_try),
            (call_script, "script_fc_menu_close", ":player"),
        (try_end),
    ]),

    # In a player's context: the menu is done; the party leaves its encounter.
    ("fc_menu_close", [
        (store_script_param, ":player", 1),
        (troop_set_slot, "$fc_player_troop", fc_slot_troop_menu, 0),
        (call_script, "script_fc_leave_battle", "$fc_main_party"),
        (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_menu_close, 0, 0),
    ]),

    # In a player's context, after native code ran: what it asked for.
    ("fc_menu_after", [
        (store_script_param, ":player", 1),
        (store_script_param, ":fallback_close", 2),
        (try_begin),
            (eq, "$fc_unavailable", 1),
            (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_notice, fc_notice_unavailable, 0),
            (call_script, "script_fc_menu_show", ":player"),
        (else_try),
            (gt, "$fc_screen_kind", 0),
            (call_script, "script_fc_items_session_start", ":player"),
        (else_try),
            (gt, "$fc_talk_request", 0),
            (store_sub, ":troop", "$fc_talk_request", 1),
            (assign, "$fc_talk_request", 0),
            (try_begin),
                (gt, "$fc_next_menu", 0),   # a jump before the conversation: the menu after it
                (troop_set_slot, "$fc_player_troop", fc_slot_troop_menu, "$fc_next_menu"),
            (try_end),
            (assign, "$fc_next_menu", 0),
            (assign, "$fc_menu_close", 0),
            (call_script, "script_fc_dialog_begin", ":player", ":troop", "$fc_talk_state"),
        (else_try),
            (eq, "$fc_menu_close", 1),
            (call_script, "script_fc_menu_close", ":player"),
        (else_try),
            (gt, "$fc_next_menu", 0),
            (troop_set_slot, "$fc_player_troop", fc_slot_troop_menu, "$fc_next_menu"),
            (call_script, "script_fc_menu_show", ":player"),
        (else_try),
            (eq, ":fallback_close", 1),
            (call_script, "script_fc_menu_close", ":player"),
        (else_try),
            (call_script, "script_fc_menu_show", ":player"),
        (try_end),
    ]),

    # Input: the player's party, encountered party, encountered party 2. From game_event_party_encounter.
    ("fc_encounter", [
        (store_script_param, ":party", 1),
        (store_script_param, ":encountered", 2),
        (store_script_param, ":encountered_2", 3),
        (store_sub, ":slot", ":party", "p_fc_player_party_0"),
        (store_add, ":troop", "trp_fc_player_0", ":slot"),
        (troop_get_slot, ":owner", ":troop", fc_slot_troop_owner),
        (gt, ":owner", 0),
        (store_sub, ":player", ":owner", 1),
        (player_is_active, ":player"),
        (call_script, "script_cf_fc_ctx_enter", ":player"),
        (assign, "$fc_next_menu", 0),
        (assign, "$fc_menu_close", 0),
        (assign, "$fc_unavailable", 0),
        (assign, "$fc_screen_kind", 0),
            (assign, "$fc_talk_request", 0),
        (try_begin),
            (call_script, "script_game_event_party_encounter", ":encountered", ":encountered_2"),
        (try_end),
        (assign, "$fc_unavailable", 0),
        (call_script, "script_fc_menu_after", ":player", 1),
        (call_script, "script_fc_ctx_leave"),
    ]),

    # Client chose option k of menu.
    ("fc_menu_choice", [
        (store_script_param, ":player", 1),
        (store_script_param, ":menu", 2),
        (store_script_param, ":k", 3),
        (call_script, "script_cf_fc_ctx_enter", ":player"),   # fails (ends this script) without a character
        (try_begin),
            (eq, ":menu", fc_dialog_menu_no),
            (troop_slot_ge, "$fc_player_troop", fc_slot_troop_dialog, 1),
            (call_script, "script_fc_dialog_choice", ":player", ":k"),
        (else_try),
            (troop_get_slot, ":current", "$fc_player_troop", fc_slot_troop_menu),
            (store_add, ":expected", ":menu", 1),
            (eq, ":current", ":expected"),
            (ge, ":menu", 0),
            (assign, "$fc_next_menu", 0),
            (assign, "$fc_menu_close", 0),
            (assign, "$fc_unavailable", 0),
            (assign, "$fc_screen_kind", 0),
            (assign, "$fc_talk_request", 0),
            (store_add, ":script", "script_fc_mk_0", ":menu"),
            (try_begin),
                (call_script, ":script", ":k"),
            (try_end),
            (call_script, "script_fc_menu_after", ":player", 0),
            (try_begin),
                (troop_slot_eq, "$fc_player_troop", fc_slot_troop_screen_kind, 0),
                (call_script, "script_fc_send_inventory", ":player", 0, "$fc_player_troop"),
            (try_end),
        (else_try),
            # stale choice (the menu changed meanwhile): show the current one again
            (gt, ":current", 0),
            (call_script, "script_fc_menu_show", ":player"),
        (try_end),
        (call_script, "script_fc_ctx_leave"),
    ]),
]

encounter_entry = [
    # on the campaign server, for a player's party (parameter 3): run this script in that player's context
    (assign, ":fc_handled", 0),
    (try_begin),
        (multiplayer_is_server),
        (multiplayer_is_campaign),
        (eq, "$fc_ctx_player", 0),
        (store_script_param, ":fc_party", 3),
        (store_add, ":fc_end", "p_fc_player_party_0", fc_max_players),
        (is_between, ":fc_party", "p_fc_player_party_0", ":fc_end"),
        (store_script_param_1, ":fc_encountered"),
        (store_script_param_2, ":fc_encountered_2"),
        (call_script, "script_fc_encounter", ":fc_party", ":fc_encountered", ":fc_encountered_2"),
        (assign, ":fc_handled", 1),
    (try_end),
    (eq, ":fc_handled", 0),
]

simulate_guard = [
    # until M4: a battle event with a player's party is never simulated (the player decides in the menu)
    (assign, ":fc_skip", 0),
    (try_begin),
        (multiplayer_is_server),
        (multiplayer_is_campaign),
        (store_script_param_1, ":fc_defender"),
        (store_script_param_2, ":fc_attacker"),
        (store_add, ":fc_end", "p_fc_player_party_0", fc_max_players),
        (this_or_next | is_between, ":fc_defender", "p_fc_player_party_0", ":fc_end"),
        (is_between, ":fc_attacker", "p_fc_player_party_0", ":fc_end"),
        (set_trigger_result, 0),
        (assign, ":fc_skip", 1),
    (try_end),
    (eq, ":fc_skip", 0),
]

# ---------------------------------------------------------------- client side

client_scripts = [
    ("fc_client_menu_reset", [
        (try_begin),
            (eq, "$fc_menu_dict_ok", 0),
            (dict_create, "$fc_menu_dict"),
            (assign, "$fc_menu_dict_ok", 1),
        (try_end),
        (dict_clear, "$fc_menu_dict"),
        (assign, "$fc_menu_count", 0),
        (assign, "$fc_menu_field", -1),
    ]),

    # Input: field (-1 = text, else the native option index): following text pieces go there.
    ("fc_client_menu_field", [
        (store_script_param, ":k", 1),
        (try_begin),
            (eq, ":k", -1),
            (assign, "$fc_menu_field", -1),
            (str_store_string, s65, "@t"),
        (else_try),
            (lt, "$fc_menu_count", MAX_SHOWN_OPTIONS),
            (assign, "$fc_menu_field", "$fc_menu_count"),
            (val_add, "$fc_menu_count", 1),
            (assign, reg60, "$fc_menu_field"),
            (str_store_string, s65, "@k{reg60}"),
            (dict_set_int, "$fc_menu_dict", s65, ":k"),
            (str_store_string, s65, "@o{reg60}"),
        (else_try),
            (assign, "$fc_menu_field", -2),   # more options than the client can show: dropped
        (try_end),
        (try_begin),
            (ge, "$fc_menu_field", -1),
            (str_clear, s66),
            (dict_set_str, "$fc_menu_dict", s65, s66),
        (try_end),
    ]),

    # s0 = a piece of text for the current field
    ("fc_client_menu_text", [
        (ge, "$fc_menu_field", -1),
        (try_begin),
            (eq, "$fc_menu_field", -1),
            (str_store_string, s65, "@t"),
        (else_try),
            (assign, reg60, "$fc_menu_field"),
            (str_store_string, s65, "@o{reg60}"),
        (try_end),
        (dict_get_str, s66, "$fc_menu_dict", s65),
        (str_store_string, s66, "@{s66}{s0}"),
        (dict_set_str, "$fc_menu_dict", s65, s66),
    ]),
]


def _remote_menu():
    options = []
    for j in range(MAX_SHOWN_OPTIONS):
        reg = s41 + j
        options.append(("fc_ro_%d" % j, [
            (lt, j, "$fc_menu_count"),
            (str_store_string, s65, "@o%d" % j),
            (dict_get_str, reg, "$fc_menu_dict", s65),
        ], "{s%d}" % (41 + j), [
            (str_store_string, s65, "@k%d" % j),
            (dict_get_int, ":k", "$fc_menu_dict", s65),
            (multiplayer_send_3_int_to_server, fc_event, fc_msg_menu_choice, "$fc_menu_no", ":k"),
        ]))
    return ("fc_remote", 0, "{s40}", "none", [
        (try_begin),
            (call_script, "script_fc_client_screen_done"),   # back from a trade/loot screen (fc_items)
        (try_end),
        (str_store_string, s65, "@t"),
        (dict_get_str, s40, "$fc_menu_dict", s65),
        (try_begin),
            (ge, "$fc_menu_mesh", 0),
            (set_background_mesh, "$fc_menu_mesh"),
        (try_end),
    ], options)


def _scripts_from_menus(native_scripts):
    menus = _native_menus()
    made = _menu_scripts(menus) + _context_scripts()
    return made + _op_scripts()


patches = [
    # first, so they touch only native's entries (the menu scripts are made from native menus, rewritten the same way)
    fp.edit_all("scripts", _rewrite_script, origin="fc_menus"),
    fp.edit_all("simple_triggers", _rewrite_simple_trigger, origin="fc_menus"),
    fp.edit_all("triggers", _rewrite_trigger, origin="fc_menus"),
    fp.edit_all("game_menus", _rewrite_menu, origin="fc_menus"),
    fp.add("scripts", server_scripts + client_scripts, origin="fc_menus"),
    fp.add_from("scripts", _scripts_from_menus, origin="fc_menus"),
    fp.prepend_ops("scripts", "game_event_party_encounter", encounter_entry, origin="fc_menus"),
    fp.prepend_ops("scripts", "game_event_simulate_battle", simulate_guard, origin="fc_menus"),
    fp.add("game_menus", [_remote_menu()], origin="fc_menus"),
]
