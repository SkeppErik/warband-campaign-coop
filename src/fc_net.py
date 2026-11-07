"""Our network messages (docs/protocol.md): one multiplayer event id (fc_event) carries every message, with the
message type first and up to three values after it.

Received in native's game_receive_network_message: the ops added at its start hand our event to fc_net_received;
native's own events pass through untouched.
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
        (try_begin),
            (multiplayer_is_server),
            (assign, reg0, ":sender"),
            (assign, reg1, ":msg"),
            (display_message, "@[fc] unknown message {reg1} from player {reg0}"),
        (else_try),
            # client
            (eq, ":msg", fc_msg_your_party),
            (call_script, "script_fc_client_set_own_party", ":v1"),
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
]

patches = [
    fp.add("scripts", scripts, origin="fc_net"),
    fp.prepend_ops("scripts", "game_receive_network_message", receive, origin="fc_net"),
]
