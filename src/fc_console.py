"""Commands for the dedicated campaign server's console (and RCON), through WSE2's
script_wse_console_command_received (called after the server's own commands; the typed text is in s0; a non-zero
trigger result means handled, the result string is shown).

    fc_save         save the world now (the server's --save-no slot)
    fc_characters   list the pool characters: who they belong to, who is connected
"""
from header_common import *
from header_operations import *
from module_constants import *
import fcpatch as fp


def _command(name, body):
    return [
        (try_begin),
            (str_store_string, s1, "@" + name),
            (str_equals, s0, s1, 1),
        ] + body + [
            (set_trigger_result, 1),
        (try_end),
    ]


console = (
    _command("fc_save", [
        (call_script, "script_fc_save_world"),
        (str_store_string, s2, "@[fc] world saved"),
        (set_result_string, s2),
    ])
    + _command("fc_characters", [
        (assign, ":fc_count", 0),
        (try_for_range, ":fc_i", 0, fc_max_players),
            (store_add, ":fc_troop", "trp_fc_player_0", ":fc_i"),
            (troop_slot_eq, ":fc_troop", fc_slot_troop_bound, 1),
            (val_add, ":fc_count", 1),
            (str_store_troop_name, s3, ":fc_troop"),
            (troop_get_slot, ":fc_owner", ":fc_troop", fc_slot_troop_owner),
            (assign, reg1, ":fc_i"),
            (try_begin),
                (gt, ":fc_owner", 0),
                (store_sub, reg2, ":fc_owner", 1),
                (display_message, "@[fc] character {reg1}: {s3}, connected as player {reg2}"),
            (else_try),
                (display_message, "@[fc] character {reg1}: {s3}, away"),
            (try_end),
        (try_end),
        (assign, reg1, ":fc_count"),
        (str_store_string, s2, "@[fc] {reg1} of %d characters taken" % fc_max_players),
        (set_result_string, s2),
    ])
)

patches = [
    fp.append_ops("scripts", "wse_console_command_received", console, origin="fc_console"),
]
