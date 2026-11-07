"""Conversations on the campaign server, shown on the client (M3, docs/encounters.md "Conversations").

Like the menus: native's dialogs run on the server in the player's context and the client shows them in the remote
menu (the NPC's line as the text, the player's lines as the options). The build makes, from every native dialog
sentence, a conditions script (cf_fc_dc_N) and a consequences script (cf_fc_dx_N) where they aren't empty, and one
script per dialog state (fc_ds_S, contiguous) that
  part 0: says the NPC's line: the first sentence of the state whose speaker matches and whose conditions pass
          (sends its text, runs its consequences, $fc_dialog_next = its next state, $fc_dialog_auto);
  part 1: sends the player's lines of the state whose conditions pass (repeat_for_* lines once per object);
  part 2: runs the chosen player line (re-checking its conditions) and sets $fc_dialog_next.
Engine rules followed: a conversation starts at "start" (change_screen_map_conversation) or "event_triggered"
(start_map_conversation); "close_window" ends it; what the consequences asked for (another menu, closing, a trade
screen) happens when it ends (a trade screen in the middle continues the conversation afterwards).
"""
from header_common import *
from header_operations import *
from header_dialogs import *
from module_constants import *
import fcpatch as fp

CONTINUE = -1            # the client's "Continue." option
REPEAT_STRIDE = 4096     # option k = sentence + REPEAT_STRIDE * repeat object
DIALOG_MENU_NO = fc_dialog_menu_no   # menu_no the client echoes for a conversation


def _native_dialogs():
    from fcnative_module_dialogs import dialogs
    return dialogs


_state_ids = None


def state_ids():
    """dialog state name -> our number (every input and output state, in order of first appearance)"""
    global _state_ids
    if _state_ids is None:
        ids = {}
        for d in _native_dialogs():
            for name in (d[1], d[4]):
                if name not in ids:
                    ids[name] = len(ids)
        for name in ("start", "event_triggered", "close_window"):
            if name not in ids:
                ids[name] = len(ids)
        _state_ids = ids
    return _state_ids


def _speaker_check(speaker):
    troop = speaker & 0xfff
    if troop == 0xfff:
        return []
    if speaker & party_tpl:
        return [(party_get_template_id, ":fc_template", "$fc_talk_party"), (eq, ":fc_template", troop)]
    return [(eq, "$fc_talk_troop", troop)]


def _repeat_range(kind):
    """(begin, end) of the objects a repeat_for_* line goes through; end may be a global"""
    if kind == 1:   # factions
        from fcnative_module_factions import factions
        return 0, len(factions)
    if kind == 2:   # parties
        return 0, "$fc_num_parties"
    if kind == 3:   # troops
        from fcnative_module_troops import troops
        return 0, len(troops)
    if kind == 4:
        return 0, 100
    return 0, 1000


def _cond_call(i, has_cond):
    if not has_cond:
        return [(assign, "$fc_ok", 1)]
    return [(assign, "$fc_ok", 0), (try_begin), (call_script, "script_cf_fc_dc_%d" % i), (try_end)]


def _cons_call(i, has_cons):
    if not has_cons:
        return []
    return [(try_begin), (call_script, "script_cf_fc_dx_%d" % i), (try_end)]


def _scripts(native_scripts):
    import fc_menus
    dialogs = _native_dialogs()
    ids = state_ids()
    conds, conss = [], []
    npc = dict((s, []) for s in ids.values())
    plyr_lines = dict((s, []) for s in ids.values())
    for i, d in enumerate(dialogs):
        speaker, cond, text, out, cons = d[0], d[2], d[3], ids[d[4]], d[5]
        if cond:
            conds.append(("cf_fc_dc_%d" % i, fc_menus.rewrite(cond) + [(assign, "$fc_ok", 1)]))
        if cons:
            conss.append(("cf_fc_dx_%d" % i, fc_menus.rewrite(cons)))
        entry = (i, speaker, bool(cond), text, out, bool(cons))
        (plyr_lines if speaker & plyr else npc)[ids[d[1]]].append(entry)

    states = []
    for name, s in sorted(ids.items(), key=lambda kv: kv[1]):
        say, offer, choose = [], [], []
        for (i, speaker, has_cond, text, out, has_cons) in npc[s]:
            say += [
                (try_begin),
                    (eq, ":found", 0),
                ] + _speaker_check(speaker) + _cond_call(i, has_cond) + [
                    (eq, "$fc_ok", 1),
                    (assign, ":found", 1),
                    (str_store_string, s67, "@" + text),
                    (str_store_troop_name, s66, "$fc_talk_troop"),
                    (str_store_string, s67, "@{s66}: {s67}"),
                    (call_script, "script_fc_send_field", ":player", -1),
                ] + _cons_call(i, has_cons) + [
                    (assign, "$fc_dialog_next", out),
                    (assign, "$fc_dialog_auto", 1 if speaker & auto_proceed else 0),
                (try_end),
            ]
        for (i, speaker, has_cond, text, out, has_cons) in plyr_lines[s]:
            kind = (speaker >> 12) & 7
            show = _speaker_check(speaker) + _cond_call(i, has_cond) + [
                (eq, "$fc_ok", 1),
                (str_store_string, s67, "@" + text),
            ]
            if kind:
                begin, end = _repeat_range(kind)
                offer += [
                    (try_for_range, ":fc_object", begin, end),
                        (assign, "$fc_repeat_object", ":fc_object"),
                    ] + show + [
                        (store_mul, ":fc_k", ":fc_object", REPEAT_STRIDE),
                        (val_add, ":fc_k", i),
                        (call_script, "script_fc_send_field", ":player", ":fc_k"),
                        (val_add, "$fc_dialog_options", 1),
                    (try_end),
                ]
            else:
                offer += [(try_begin)] + show + [
                    (call_script, "script_fc_send_field", ":player", i),
                    (val_add, "$fc_dialog_options", 1),
                (try_end)]
            choose += [
                (try_begin),
                    (eq, ":sentence", i),
                    (assign, "$fc_repeat_object", ":object"),
                ] + _speaker_check(speaker) + _cond_call(i, has_cond) + [
                    (eq, "$fc_ok", 1),
                ] + _cons_call(i, has_cons) + [
                    (assign, "$fc_dialog_next", out),
                (try_end),
            ]
        states.append(("fc_ds_%d" % s, [
            (store_script_param, ":player", 1),
            (store_script_param, ":part", 2),
            (store_script_param, ":sentence", 3),
            (store_script_param, ":object", 4),
            (assign, ":found", 0),
            (try_begin),
                (eq, ":part", 0),
            ] + say + [
            (else_try),
                (eq, ":part", 1),
            ] + offer + [
            (else_try),
                (eq, ":part", 2),
            ] + choose + [
            (try_end),
        ]))
    return states + conds + conss


CLOSE = None   # filled at build time (state ids need the native dialogs)


def _flow_scripts(native_scripts):
    ids = state_ids()
    close = ids["close_window"]
    return [
        # In a player's context: start a conversation with troop at state.
        ("fc_dialog_begin", [
            (store_script_param, ":player", 1),
            (store_script_param, ":troop", 2),
            (store_script_param, ":state", 3),
            (assign, "$fc_talk_troop", ":troop"),
            (assign, "$fc_talk_party", "$g_encountered_party"),
            (assign, "$fc_next_menu", 0),
            (assign, "$fc_menu_close", 0),
            (try_for_parties, ":p"),
                (store_add, "$fc_num_parties", ":p", 1),
            (try_end),
            (call_script, "script_fc_dialog_npc", ":player", ":state"),
        ]),

        # In a player's context: the NPC speaks in state (then the player's lines, or "Continue.").
        ("fc_dialog_npc", [
            (store_script_param, ":player", 1),
            (store_script_param, ":state", 2),
            (call_script, "script_fc_flags_reset"),
            (assign, "$fc_talk_request", 0),
            (assign, "$fc_dialog_next", -1),
            (assign, "$fc_dialog_auto", 0),
            (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_menu_open, DIALOG_MENU_NO, -1),
            (store_add, ":script", "script_fc_ds_0", ":state"),
            (try_begin),
                (call_script, ":script", ":player", 0, 0, 0),
            (try_end),
            (assign, ":next", "$fc_dialog_next"),
            (try_begin),
                (eq, ":next", -1),   # nobody has anything to say: the conversation is over
                (call_script, "script_fc_dialog_end", ":player"),
            (else_try),
                (eq, "$fc_unavailable", 1),
                (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_notice, fc_notice_unavailable, 0),
                (call_script, "script_fc_dialog_end", ":player"),
            (else_try),
                (gt, "$fc_screen_kind", 0),
                (store_add, ":slot_value", ":next", 1),
                (troop_set_slot, "$fc_player_troop", fc_slot_troop_dialog, ":slot_value"),
                (troop_set_slot, "$fc_player_troop", fc_slot_troop_dialog_pending, 1),
                (call_script, "script_fc_items_session_start", ":player"),
            (else_try),
                (assign, "$fc_dialog_options", 0),
                (try_begin),
                    (neq, ":next", close),
                    (eq, "$fc_dialog_auto", 0),
                    (store_add, ":script", "script_fc_ds_0", ":next"),
                    (try_begin),
                        (call_script, ":script", ":player", 1, 0, 0),
                    (try_end),
                (try_end),
                (store_add, ":slot_value", ":next", 1),
                (troop_set_slot, "$fc_player_troop", fc_slot_troop_dialog, ":slot_value"),
                (try_begin),
                    (eq, "$fc_dialog_options", 0),
                    (troop_set_slot, "$fc_player_troop", fc_slot_troop_dialog_pending, 1),
                    (str_store_string, s67, "@Continue."),
                    (call_script, "script_fc_send_field", ":player", CONTINUE),
                (else_try),
                    (troop_set_slot, "$fc_player_troop", fc_slot_troop_dialog_pending, 0),
                (try_end),
                (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_menu_show, DIALOG_MENU_NO, 0),
            (try_end),
        ]),

        # In a player's context: the player chose option k in the conversation.
        ("fc_dialog_choice", [
            (store_script_param, ":player", 1),
            (store_script_param, ":k", 2),
            (troop_get_slot, ":state", "$fc_player_troop", fc_slot_troop_dialog),
            (val_sub, ":state", 1),
            (ge, ":state", 0),
            (troop_get_slot, ":pending", "$fc_player_troop", fc_slot_troop_dialog_pending),
            (try_begin),
                (eq, ":pending", 1),
                # after "Continue.": the NPC goes on in the state its line led to
                (try_begin),
                    (eq, ":state", close),
                    (call_script, "script_fc_dialog_end", ":player"),
                (else_try),
                    (call_script, "script_fc_dialog_npc", ":player", ":state"),
                (try_end),
            (else_try),
                (ge, ":k", 0),
                (store_mod, ":sentence", ":k", REPEAT_STRIDE),
                (store_div, ":object", ":k", REPEAT_STRIDE),
                (call_script, "script_fc_flags_reset"),
                (assign, "$fc_dialog_next", -2),
                (store_add, ":script", "script_fc_ds_0", ":state"),
                (try_begin),
                    (call_script, ":script", ":player", 2, ":sentence", ":object"),
                (try_end),
                (assign, ":next", "$fc_dialog_next"),
                (try_begin),
                    (eq, ":next", -2),   # not an option of this state (any more): say the NPC's line again
                    (call_script, "script_fc_dialog_npc", ":player", ":state"),
                (else_try),
                    (eq, "$fc_unavailable", 1),
                    (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_notice, fc_notice_unavailable,
                     0),
                    (call_script, "script_fc_dialog_end", ":player"),
                (else_try),
                    (gt, "$fc_screen_kind", 0),
                    (store_add, ":slot_value", ":next", 1),
                    (troop_set_slot, "$fc_player_troop", fc_slot_troop_dialog, ":slot_value"),
                    (troop_set_slot, "$fc_player_troop", fc_slot_troop_dialog_pending, 1),
                    (call_script, "script_fc_items_session_start", ":player"),
                (else_try),
                    (eq, ":next", close),
                    (call_script, "script_fc_dialog_end", ":player"),
                (else_try),
                    (call_script, "script_fc_dialog_npc", ":player", ":next"),
                (try_end),
            (try_end),
        ]),

        # In a player's context: the conversation is over; then what its consequences asked for (or the menu again).
        ("fc_dialog_end", [
            (store_script_param, ":player", 1),
            (troop_set_slot, "$fc_player_troop", fc_slot_troop_dialog, 0),
            (troop_set_slot, "$fc_player_troop", fc_slot_troop_dialog_pending, 0),
            (assign, "$fc_talk_troop", -1),
            (assign, "$fc_unavailable", 0),
            (assign, "$fc_screen_kind", 0),
            (assign, "$fc_talk_request", 0),
            (call_script, "script_fc_menu_after", ":player", 0),
        ]),
    ]


patches = [
    fp.add_from("scripts", _flow_scripts, origin="fc_dialogs"),
    fp.add_from("scripts", _scripts, origin="fc_dialogs"),
]
