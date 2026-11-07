"""Our network messages (docs/protocol.md): one multiplayer event id (fc_event) carries every message, with the
message type first and up to three values after it.

Received in native's game_receive_network_message: the ops added at its start hand our event to fc_net_received
(ints) or to fc_client_menu_text (fc_event_text strings, s0); native's own events pass through untouched.
"""
from header_common import *
from header_operations import *
from module_constants import *
import fcpatch as fp

scripts = [
    # Input: sender player_no (0 on a client: the server), message type, value 1-3.
    ("fc_net_received", [
        (store_script_param, ":sender", 1),
        (store_script_param, ":msg", 2),
        (store_script_param, ":v1", 3),
        (store_script_param, ":v2", 4),
        (try_begin),
            (multiplayer_is_server),
            (eq, ":msg", fc_msg_menu_choice),
            (call_script, "script_fc_menu_choice", ":sender", ":v1", ":v2"),
        (else_try),
            (multiplayer_is_server),
            (assign, reg0, ":sender"),
            (assign, reg1, ":msg"),
            (display_message, "@[fc] unknown message {reg1} from player {reg0}"),
        (else_try),
            # client
            (eq, ":msg", fc_msg_your_party),
            (call_script, "script_fc_client_set_own_party", ":v1"),
        (else_try),
            (eq, ":msg", fc_msg_menu_open),
            (call_script, "script_fc_client_menu_reset"),
            (assign, "$fc_menu_no", ":v1"),
            (assign, "$fc_menu_mesh", ":v2"),
        (else_try),
            (eq, ":msg", fc_msg_menu_field),
            (call_script, "script_fc_client_menu_field", ":v1"),
        (else_try),
            (eq, ":msg", fc_msg_menu_show),
            (jump_to_menu, "mnu_fc_remote"),
        (else_try),
            (eq, ":msg", fc_msg_menu_close),
            (change_screen_return),
        (else_try),
            (eq, ":msg", fc_msg_notice),
            (eq, ":v1", fc_notice_unavailable),
            (display_message, "@This is not available in co-op yet."),
        (else_try),
            (assign, reg1, ":msg"),
            (display_message, "@[fc] unknown message {reg1} from the server"),
        (try_end),
    ]),
]

receive = [
    (try_begin),
        (store_script_param, ":fc_event", 2),
        (eq, ":fc_event", fc_event),
        (store_script_param, ":fc_sender", 1),
        (store_script_param, ":fc_msg", 3),
        (store_script_param, ":fc_v1", 4),
        (store_script_param, ":fc_v2", 5),
        (store_script_param, ":fc_v3", 6),
        (call_script, "script_fc_net_received", ":fc_sender", ":fc_msg", ":fc_v1", ":fc_v2", ":fc_v3"),
    (try_end),
    (try_begin),
        # a text piece for the menu (client; the text is in s0)
        (store_script_param, ":fc_text_event", 2),
        (eq, ":fc_text_event", fc_event_text),
        (neg | multiplayer_is_server),
        (call_script, "script_fc_client_menu_text"),
    (try_end),
    (try_begin),
        # a message from native code the server ran for this player (client; s0)
        (store_script_param, ":fc_message_event", 2),
        (eq, ":fc_message_event", fc_event_message),
        (neg | multiplayer_is_server),
        (display_message, s0),
    (try_end),
]

patches = [
    fp.add("scripts", scripts, origin="fc_net"),
    fp.prepend_ops("scripts", "game_receive_network_message", receive, origin="fc_net"),
]
