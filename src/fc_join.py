"""Joining the co-op campaign from the game (M1).

WSE2's own "Join campaign" button didn't appear on the multiplayer screen, so the first menu of a new game
(native's start_game_0, after "Start a new game") offers to connect to a campaign server with WSE2's
multiplayer_connect_to_server and its campaign flag. For now the address is this PC; an address field comes later.
"""
from header_common import *
from header_operations import *
from header_game_menus import *
from module_constants import *
import fcpatch as fp


def _connect(address):
    return [
        (str_store_string, s0, "@" + address),
        (str_clear, s1),
        (display_message, "@[fc] connecting to the campaign server at {s0}..."),
        (multiplayer_connect_to_server, s0, s1, 1),
    ]


patches = [
    # Two forms of the address until we know which one WSE2 expects.
    fp.add_menu_option("start_game_0", ("fc_join_local", [], "Join the co-op campaign on this PC.",
                                        _connect("127.0.0.1")), before="go_back", origin="fc_join"),
    fp.add_menu_option("start_game_0", ("fc_join_local_port", [], "Join the co-op campaign on this PC (port 7240).",
                                        _connect("127.0.0.1:7240")), before="go_back", origin="fc_join"),
]
