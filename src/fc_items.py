"""Trade, loot and the player's own inventory (M3, docs/encounters.md "Items").

The engine never sends troop inventories or troop gold to clients, so we do:
- A menu option that opens the trade or loot screen (change_screen_trade / change_screen_loot, in a player's
  context) starts a screen session: the server sends the player's inventory, the other troop's inventory, and for
  trade the price factors of every item involved (native's price scripts, run for that player); the client fills
  its copies of both troops and opens the native screen. Back in the menu, the client sends both inventories; the
  server checks that no item or gold was made (items counted per kind over both troops, gold summed), applies
  them, updates town prices like native's buy/sell events, and shows the menu again. One player per merchant.
- The player's own inventory window: the client sends its inventory when it is back on the map after a window
  opened; the server accepts rearranging and dropping (no new items, same gold).
- The server sends the player's inventory on join and after every menu action (menus change gold and items).

Inventories travel as (side*1000 + slot, item, modifier*10000 + amount); side 0 = the player's troop, 1 = the other.
Received inventories wait in a WSE2 dictionary (no buffer troops: new troops would break existing saves).
"""
from header_common import *
from header_operations import *
from header_triggers import *
from module_constants import *
import fcpatch as fp

SCREEN_TRADE = 1
SCREEN_LOOT = 2

_pack = [
    # Input: item, modifier, amount. reg0 = one int (-1 = empty)
    ("fc_items_pack", [
        (store_script_param, ":item", 1),
        (store_script_param, ":modifier", 2),
        (store_script_param, ":amount", 3),
        (try_begin),
            (lt, ":item", 0),
            (assign, reg0, -1),
        (else_try),
            (store_mul, reg0, ":amount", 64),
            (val_add, reg0, ":modifier"),
            (val_mul, reg0, 2000),
            (val_add, reg0, ":item"),
        (try_end),
    ]),
    # Input: packed. reg0 = item, reg1 = modifier, reg2 = amount
    ("fc_items_unpack", [
        (store_script_param, ":packed", 1),
        (try_begin),
            (lt, ":packed", 0),
            (assign, reg0, -1),
            (assign, reg1, 0),
            (assign, reg2, 0),
        (else_try),
            (store_mod, reg0, ":packed", 2000),
            (store_div, ":rest", ":packed", 2000),
            (store_mod, reg1, ":rest", 64),
            (store_div, reg2, ":rest", 64),
        (try_end),
    ]),
]

common_scripts = _pack + [
    # Input: troop. Empties its inventory (equipment too) and takes its gold.
    ("fc_items_clear", [
        (store_script_param, ":troop", 1),
        (troop_get_inventory_capacity, ":cap", ":troop"),
        (try_for_range, ":slot", 0, ":cap"),
            (troop_set_inventory_slot, ":troop", ":slot", -1),
        (try_end),
        (store_troop_gold, ":gold", ":troop"),
        (try_begin),
            (gt, ":gold", 0),
            (troop_remove_gold, ":troop", ":gold"),
        (try_end),
    ]),

    # Input: troop, slot, item, modifier, amount.
    ("fc_items_set_slot", [
        (store_script_param, ":troop", 1),
        (store_script_param, ":slot", 2),
        (store_script_param, ":item", 3),
        (store_script_param, ":modifier", 4),
        (store_script_param, ":amount", 5),
        (troop_get_inventory_capacity, ":cap", ":troop"),
        (is_between, ":slot", 0, ":cap"),
        (troop_set_inventory_slot, ":troop", ":slot", ":item"),
        (try_begin),
            (ge, ":item", 0),
            (troop_set_inventory_slot_modifier, ":troop", ":slot", ":modifier"),
            (gt, ":amount", 0),
            (troop_inventory_slot_set_item_amount, ":troop", ":slot", ":amount"),
        (try_end),
    ]),
]

# ---------------------------------------------------------------- server

def _key(prefix):
    """ops: s65 = "<prefix>{reg60}_{reg61}" (reg60, reg61 set by the caller)"""
    return (str_store_string, s65, "@" + prefix + "{reg60}_{reg61}")


server_scripts = [
    ("fc_items_dict", [
        (try_begin),
            (eq, "$fc_items_dict_ok", 0),
            (dict_create, "$fc_items_dict"),
            (assign, "$fc_items_dict_ok", 1),
        (try_end),
    ]),

    # Input: player, side, troop. Sends that inventory and gold to the player.
    ("fc_send_inventory", [
        (store_script_param, ":player", 1),
        (store_script_param, ":side", 2),
        (store_script_param, ":troop", 3),
        (store_troop_gold, ":gold", ":troop"),
        (multiplayer_send_4_int_to_player, ":player", fc_event, fc_msg_inv_begin, ":side", ":troop", ":gold"),
        (troop_get_inventory_capacity, ":cap", ":troop"),
        (try_for_range, ":slot", 0, ":cap"),
            (troop_get_inventory_slot, ":item", ":troop", ":slot"),
            (ge, ":item", 0),
            (troop_get_inventory_slot_modifier, ":modifier", ":troop", ":slot"),
            (troop_inventory_slot_get_item_amount, ":amount", ":troop", ":slot"),
            (store_mul, ":where", ":side", 1000),
            (val_add, ":where", ":slot"),
            (store_mul, ":extra", ":modifier", 10000),
            (val_add, ":extra", ":amount"),
            (multiplayer_send_4_int_to_player, ":player", fc_event, fc_msg_inv_slot, ":where", ":item", ":extra"),
        (try_end),
        (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_inv_end, ":side", 0),
    ]),

    # Input: player, troop. Price factors (native's scripts, in the player's context) of every item the troop has.
    ("fc_send_prices", [
        (store_script_param, ":player", 1),
        (store_script_param, ":troop", 2),
        (troop_get_inventory_capacity, ":cap", ":troop"),
        (try_for_range, ":slot", 0, ":cap"),
            (troop_get_inventory_slot, ":item", ":troop", ":slot"),
            (ge, ":item", 0),
            (call_script, "script_game_get_item_buy_price_factor", ":item"),
            (assign, ":buy", reg0),
            (call_script, "script_game_get_item_sell_price_factor", ":item"),
            (assign, ":sell", reg0),
            (multiplayer_send_4_int_to_player, ":player", fc_event, fc_msg_price, ":item", ":buy", ":sell"),
        (try_end),
    ]),

    # From the client: an inventory begins (side, gold). The player's buffer is emptied.
    ("fc_items_receive_begin", [
        (store_script_param, ":player", 1),
        (store_script_param, ":side", 2),
        (store_script_param, ":gold", 3),
        (call_script, "script_fc_items_dict"),
        (assign, reg60, ":player"),
        (try_for_range, ":slot", 0, fc_items_max_slots),
            (store_mul, reg61, ":side", 1000),
            (val_add, reg61, ":slot"),
            _key("b"),
            (dict_set_int, "$fc_items_dict", s65, -1),
        (try_end),
        (store_mul, reg61, ":side", 1000),
        (val_add, reg61, 999),
        _key("b"),
        (dict_set_int, "$fc_items_dict", s65, ":gold"),
    ]),

    # From the client: one slot (side*1000 + slot, item, modifier*10000 + amount).
    ("fc_items_receive_slot", [
        (store_script_param, ":player", 1),
        (store_script_param, ":where", 2),
        (store_script_param, ":item", 3),
        (store_script_param, ":extra", 4),
        (store_mod, ":slot", ":where", 1000),
        (lt, ":slot", fc_items_max_slots),
        (store_div, ":modifier", ":extra", 10000),
        (store_mod, ":amount", ":extra", 10000),
        (call_script, "script_fc_items_pack", ":item", ":modifier", ":amount"),
        (assign, ":packed", reg0),
        (call_script, "script_fc_items_dict"),
        (assign, reg60, ":player"),
        (assign, reg61, ":where"),
        _key("b"),
        (dict_set_int, "$fc_items_dict", s65, ":packed"),
    ]),

    # Input: player, side. reg0 = the received gold of that side.
    ("fc_items_buffer_gold", [
        (store_script_param, ":player", 1),
        (store_script_param, ":side", 2),
        (assign, reg60, ":player"),
        (store_mul, reg61, ":side", 1000),
        (val_add, reg61, 999),
        _key("b"),
        (dict_get_int, reg0, "$fc_items_dict", s65, 0),
    ]),

    # Input: player, side, slot. reg0..reg2 = the received item, modifier, amount (reg0 -1 = empty).
    ("fc_items_buffer_slot", [
        (store_script_param, ":player", 1),
        (store_script_param, ":side", 2),
        (store_script_param, ":slot", 3),
        (assign, reg60, ":player"),
        (store_mul, reg61, ":side", 1000),
        (val_add, reg61, ":slot"),
        _key("b"),
        (dict_get_int, ":packed", "$fc_items_dict", s65, -1),
        (call_script, "script_fc_items_unpack", ":packed"),
    ]),

    # Input: counter (0 = before, 1 = after), item, add. Counts item kinds in the dictionary.
    ("fc_items_count_add", [
        (store_script_param, ":counter", 1),
        (store_script_param, ":item", 2),
        (store_script_param, ":add", 3),
        (assign, reg60, ":counter"),
        (assign, reg61, ":item"),
        _key("c"),
        (dict_get_int, ":n", "$fc_items_dict", s65, 0),
        (val_add, ":n", ":add"),
        (dict_set_int, "$fc_items_dict", s65, ":n"),
    ]),

    ("fc_items_count_get", [
        (store_script_param, ":counter", 1),
        (store_script_param, ":item", 2),
        (assign, reg60, ":counter"),
        (assign, reg61, ":item"),
        _key("c"),
        (dict_get_int, reg0, "$fc_items_dict", s65, 0),
    ]),

    # Input: counter, troop. Counts the troop's items into the counter (and zeroes the other counter's keys first
    # by the caller clearing the dictionary of counts: see fc_items_counts_reset).
    ("fc_items_count_troop", [
        (store_script_param, ":counter", 1),
        (store_script_param, ":troop", 2),
        (troop_get_inventory_capacity, ":cap", ":troop"),
        (try_for_range, ":slot", 0, ":cap"),
            (troop_get_inventory_slot, ":item", ":troop", ":slot"),
            (ge, ":item", 0),
            (call_script, "script_fc_items_count_add", ":counter", ":item", 1),
        (try_end),
    ]),

    # Input: counter, player, side. Counts a received inventory into the counter.
    ("fc_items_count_buffer", [
        (store_script_param, ":counter", 1),
        (store_script_param, ":player", 2),
        (store_script_param, ":side", 3),
        (try_for_range, ":slot", 0, fc_items_max_slots),
            (call_script, "script_fc_items_buffer_slot", ":player", ":side", ":slot"),
            (ge, reg0, 0),
            (call_script, "script_fc_items_count_add", ":counter", reg0, 1),
        (try_end),
    ]),

    # Input: troop. Zeroes the counts of the items the troop has (before counting again).
    ("fc_items_counts_reset_troop", [
        (store_script_param, ":troop", 1),
        (troop_get_inventory_capacity, ":cap", ":troop"),
        (try_for_range, ":slot", 0, ":cap"),
            (troop_get_inventory_slot, ":item", ":troop", ":slot"),
            (ge, ":item", 0),
            (try_for_range, ":counter", 0, 2),
                (assign, reg60, ":counter"),
                (assign, reg61, ":item"),
                _key("c"),
                (dict_set_int, "$fc_items_dict", s65, 0),
            (try_end),
        (try_end),
    ]),

    ("fc_items_counts_reset_buffer", [
        (store_script_param, ":player", 1),
        (store_script_param, ":side", 2),
        (try_for_range, ":slot", 0, fc_items_max_slots),
            (call_script, "script_fc_items_buffer_slot", ":player", ":side", ":slot"),
            (ge, reg0, 0),
            (assign, ":item", reg0),
            (try_for_range, ":counter", 0, 2),
                (assign, reg60, ":counter"),
                (assign, reg61, ":item"),
                _key("c"),
                (dict_set_int, "$fc_items_dict", s65, 0),
            (try_end),
        (try_end),
    ]),

    # Input: troop, counter_a, counter_b, exact (1: counts must be equal; 0: a <= b). Fails if an item of the
    # troop breaks the rule.
    ("cf_fc_items_check_troop_items", [
        (store_script_param, ":troop", 1),
        (store_script_param, ":exact", 2),
        (troop_get_inventory_capacity, ":cap", ":troop"),
        (assign, ":ok", 1),
        (try_for_range, ":slot", 0, ":cap"),
            (troop_get_inventory_slot, ":item", ":troop", ":slot"),
            (ge, ":item", 0),
            (call_script, "script_fc_items_count_get", 0, ":item"),
            (assign, ":before", reg0),
            (call_script, "script_fc_items_count_get", 1, ":item"),
            (try_begin),
                (eq, ":exact", 1),
                (neq, reg0, ":before"),
                (assign, ":ok", 0),
            (else_try),
                (gt, reg0, ":before"),
                (assign, ":ok", 0),
            (try_end),
        (try_end),
        (eq, ":ok", 1),
    ]),

    ("cf_fc_items_check_buffer_items", [
        (store_script_param, ":player", 1),
        (store_script_param, ":side", 2),
        (store_script_param, ":exact", 3),
        (assign, ":ok", 1),
        (try_for_range, ":slot", 0, fc_items_max_slots),
            (call_script, "script_fc_items_buffer_slot", ":player", ":side", ":slot"),
            (ge, reg0, 0),
            (assign, ":item", reg0),
            (call_script, "script_fc_items_count_get", 0, ":item"),
            (assign, ":before", reg0),
            (call_script, "script_fc_items_count_get", 1, ":item"),
            (try_begin),
                (eq, ":exact", 1),
                (neq, reg0, ":before"),
                (assign, ":ok", 0),
            (else_try),
                (gt, reg0, ":before"),
                (assign, ":ok", 0),
            (try_end),
        (try_end),
        (eq, ":ok", 1),
    ]),

    # Input: player, side, troop. The received inventory and gold become the troop's.
    ("fc_items_apply_buffer", [
        (store_script_param, ":player", 1),
        (store_script_param, ":side", 2),
        (store_script_param, ":troop", 3),
        (call_script, "script_fc_items_clear", ":troop"),
        (troop_get_inventory_capacity, ":cap", ":troop"),
        (val_min, ":cap", fc_items_max_slots),
        (try_for_range, ":slot", 0, ":cap"),
            (call_script, "script_fc_items_buffer_slot", ":player", ":side", ":slot"),
            (ge, reg0, 0),
            (call_script, "script_fc_items_set_slot", ":troop", ":slot", reg0, reg1, reg2),
        (try_end),
        (call_script, "script_fc_items_buffer_gold", ":player", ":side"),
        (try_begin),
            (gt, reg0, 0),
            (troop_add_gold, ":troop", reg0),
        (try_end),
    ]),

    # In the player's context, trade only: native's buy/sell events (town prices) for what changed hands.
    ("fc_items_price_events", [
        (store_script_param, ":player", 1),
        (store_script_param, ":troop", 2),   # the player's troop, before the received inventory is applied
        (call_script, "script_fc_items_counts_reset_troop", ":troop"),
        (call_script, "script_fc_items_counts_reset_buffer", ":player", 0),
        (call_script, "script_fc_items_count_troop", 0, ":troop"),
        (call_script, "script_fc_items_count_buffer", 1, ":player", 0),
        # each item kind once: an item's counter is set to the "after" count when handled
        (try_for_range, ":slot", 0, fc_items_max_slots),
            (call_script, "script_fc_items_buffer_slot", ":player", 0, ":slot"),
            (ge, reg0, 0),
            (assign, ":item", reg0),
            (call_script, "script_fc_items_count_get", 0, ":item"),
            (assign, ":before", reg0),
            (call_script, "script_fc_items_count_get", 1, ":item"),
            (store_sub, ":bought", reg0, ":before"),
            (gt, ":bought", 0),
            (try_for_range, ":unused", 0, ":bought"),
                (call_script, "script_game_event_buy_item", ":item", 0),
            (try_end),
            (call_script, "script_fc_items_count_add", 0, ":item", ":bought"),
        (try_end),
        (troop_get_inventory_capacity, ":cap", ":troop"),
        (try_for_range, ":slot", 0, ":cap"),
            (troop_get_inventory_slot, ":item", ":troop", ":slot"),
            (ge, ":item", 0),
            (call_script, "script_fc_items_count_get", 0, ":item"),
            (assign, ":before", reg0),
            (call_script, "script_fc_items_count_get", 1, ":item"),
            (store_sub, ":sold", ":before", reg0),
            (gt, ":sold", 0),
            (try_for_range, ":unused", 0, ":sold"),
                (call_script, "script_game_event_sell_item", ":item", 0),
            (try_end),
            (val_mul, ":sold", -1),
            (call_script, "script_fc_items_count_add", 0, ":item", ":sold"),
        (try_end),
    ]),

    # In the player's context: a menu asked for the trade or loot screen ($fc_screen_kind, $fc_screen_troop).
    ("fc_items_session_start", [
        (store_script_param, ":player", 1),
        (assign, ":kind", "$fc_screen_kind"),
        (assign, ":other", "$fc_screen_troop"),
        (assign, "$fc_screen_kind", 0),
        # one player per merchant: fc_slot_troop_session on the other troop = pool slot + 1 of the trading player
        (store_sub, ":my_slot", "$fc_player_troop", "trp_fc_player_0"),
        (store_add, ":my_mark", ":my_slot", 1),
        (troop_get_slot, ":mark", ":other", fc_slot_troop_session),
        (assign, ":busy", 0),
        (try_begin),
            (gt, ":mark", 0),
            (neq, ":mark", ":my_mark"),
            (store_add, ":holder", "trp_fc_player_0", ":mark"),
            (val_sub, ":holder", 1),
            (troop_slot_ge, ":holder", fc_slot_troop_owner, 1),
            (troop_slot_eq, ":holder", fc_slot_troop_screen_troop, ":other"),
            (assign, ":busy", 1),
        (try_end),
        (try_begin),
            (eq, ":busy", 1),
            (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_notice, fc_notice_busy, 0),
            (call_script, "script_fc_menu_show", ":player"),
        (else_try),
            (troop_set_slot, ":other", fc_slot_troop_session, ":my_mark"),
            (troop_set_slot, "$fc_player_troop", fc_slot_troop_screen_kind, ":kind"),
            (troop_set_slot, "$fc_player_troop", fc_slot_troop_screen_troop, ":other"),
            (try_begin),
                (eq, ":kind", SCREEN_TRADE),
                (call_script, "script_fc_send_prices", ":player", ":other"),
                (call_script, "script_fc_send_prices", ":player", "$fc_player_troop"),
            (try_end),
            (call_script, "script_fc_send_inventory", ":player", 0, "$fc_player_troop"),
            (call_script, "script_fc_send_inventory", ":player", 1, ":other"),
            (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_screen_open, ":kind", ":other"),
        (try_end),
    ]),

    # In the player's context: the client is back from the screen and sent both inventories.
    ("fc_items_session_done", [
        (store_script_param, ":player", 1),
        (troop_get_slot, ":kind", "$fc_player_troop", fc_slot_troop_screen_kind),
        (troop_get_slot, ":other", "$fc_player_troop", fc_slot_troop_screen_troop),
        (gt, ":kind", 0),
        (assign, ":mine", "$fc_player_troop"),
        (call_script, "script_fc_items_dict"),
        # counts before (both troops) and after (both received inventories) must match per item kind
        (call_script, "script_fc_items_counts_reset_troop", ":mine"),
        (call_script, "script_fc_items_counts_reset_troop", ":other"),
        (call_script, "script_fc_items_counts_reset_buffer", ":player", 0),
        (call_script, "script_fc_items_counts_reset_buffer", ":player", 1),
        (call_script, "script_fc_items_count_troop", 0, ":mine"),
        (call_script, "script_fc_items_count_troop", 0, ":other"),
        (call_script, "script_fc_items_count_buffer", 1, ":player", 0),
        (call_script, "script_fc_items_count_buffer", 1, ":player", 1),
        (store_troop_gold, ":gold_before", ":mine"),
        (store_troop_gold, ":gold_other", ":other"),
        (val_add, ":gold_before", ":gold_other"),
        (call_script, "script_fc_items_buffer_gold", ":player", 0),
        (assign, ":gold_after", reg0),
        (call_script, "script_fc_items_buffer_gold", ":player", 1),
        (val_add, ":gold_after", reg0),
        (assign, ":ok", 0),
        (try_begin),
            (eq, ":gold_after", ":gold_before"),
            (call_script, "script_cf_fc_items_check_troop_items", ":mine", 1),
            (call_script, "script_cf_fc_items_check_troop_items", ":other", 1),
            (call_script, "script_cf_fc_items_check_buffer_items", ":player", 0, 1),
            (call_script, "script_cf_fc_items_check_buffer_items", ":player", 1, 1),
            (assign, ":ok", 1),
        (try_end),
        (try_begin),
            (eq, ":ok", 1),
            (try_begin),
                (eq, ":kind", SCREEN_TRADE),
                (call_script, "script_fc_items_price_events", ":player", ":mine"),
            (try_end),
            (call_script, "script_fc_items_apply_buffer", ":player", 0, ":mine"),
            (call_script, "script_fc_items_apply_buffer", ":player", 1, ":other"),
        (else_try),
            (multiplayer_send_3_int_to_player, ":player", fc_event, fc_msg_notice, fc_notice_rejected, 0),
        (try_end),
        (troop_set_slot, ":mine", fc_slot_troop_screen_kind, 0),
        (troop_set_slot, ":mine", fc_slot_troop_screen_troop, 0),
        (troop_set_slot, ":other", fc_slot_troop_session, 0),
        (call_script, "script_fc_send_inventory", ":player", 0, ":mine"),
        (call_script, "script_fc_menu_show", ":player"),
    ]),

    # In the player's context: the client sent its own inventory after an inventory/party/character window.
    ("fc_items_update", [
        (store_script_param, ":player", 1),
        (assign, ":mine", "$fc_player_troop"),
        (troop_slot_eq, ":mine", fc_slot_troop_screen_kind, 0),   # not during a screen session
        (call_script, "script_fc_items_dict"),
        (call_script, "script_fc_items_counts_reset_troop", ":mine"),
        (call_script, "script_fc_items_counts_reset_buffer", ":player", 0),
        (call_script, "script_fc_items_count_troop", 0, ":mine"),
        (call_script, "script_fc_items_count_buffer", 1, ":player", 0),
        (store_troop_gold, ":gold", ":mine"),
        (call_script, "script_fc_items_buffer_gold", ":player", 0),
        (try_begin),
            (eq, reg0, ":gold"),
            (call_script, "script_cf_fc_items_check_buffer_items", ":player", 0, 0),
            (call_script, "script_fc_items_apply_buffer", ":player", 0, ":mine"),
        (else_try),
            (call_script, "script_fc_send_inventory", ":player", 0, ":mine"),
        (try_end),
    ]),
]

# ---------------------------------------------------------------- client

client_scripts = [
    ("fc_client_prices_dict", [
        (try_begin),
            (eq, "$fc_prices_dict_ok", 0),
            (dict_create, "$fc_prices_dict"),
            (assign, "$fc_prices_dict_ok", 1),
        (try_end),
    ]),

    # Input: side, troop, gold. The server sends an inventory: empty our copy of the troop.
    ("fc_client_inv_begin", [
        (store_script_param, ":side", 1),
        (store_script_param, ":troop", 2),
        (store_script_param, ":gold", 3),
        (try_begin),
            (eq, ":side", 0),
            (assign, "$fc_inv_troop_0", ":troop"),
        (else_try),
            (assign, "$fc_inv_troop_1", ":troop"),
        (try_end),
        (call_script, "script_fc_items_clear", ":troop"),
        (try_begin),
            (gt, ":gold", 0),
            (troop_add_gold, ":troop", ":gold"),
        (try_end),
    ]),

    ("fc_client_inv_slot", [
        (store_script_param, ":where", 1),
        (store_script_param, ":item", 2),
        (store_script_param, ":extra", 3),
        (store_div, ":side", ":where", 1000),
        (store_mod, ":slot", ":where", 1000),
        (store_div, ":modifier", ":extra", 10000),
        (store_mod, ":amount", ":extra", 10000),
        (try_begin),
            (eq, ":side", 0),
            (assign, ":troop", "$fc_inv_troop_0"),
        (else_try),
            (assign, ":troop", "$fc_inv_troop_1"),
        (try_end),
        (call_script, "script_fc_items_set_slot", ":troop", ":slot", ":item", ":modifier", ":amount"),
    ]),

    ("fc_client_price", [
        (store_script_param, ":item", 1),
        (store_script_param, ":buy", 2),
        (store_script_param, ":sell", 3),
        (call_script, "script_fc_client_prices_dict"),
        (assign, reg60, ":item"),
        (str_store_string, s65, "@b{reg60}"),
        (dict_set_int, "$fc_prices_dict", s65, ":buy"),
        (str_store_string, s65, "@s{reg60}"),
        (dict_set_int, "$fc_prices_dict", s65, ":sell"),
    ]),

    # Input: side, troop. Sends our copy of the troop's inventory to the server.
    ("fc_client_send_inventory", [
        (store_script_param, ":side", 1),
        (store_script_param, ":troop", 2),
        (store_troop_gold, ":gold", ":troop"),
        (multiplayer_send_4_int_to_server, fc_event, fc_msg_inv_begin, ":side", ":troop", ":gold"),
        (troop_get_inventory_capacity, ":cap", ":troop"),
        (val_min, ":cap", fc_items_max_slots),
        (try_for_range, ":slot", 0, ":cap"),
            (troop_get_inventory_slot, ":item", ":troop", ":slot"),
            (ge, ":item", 0),
            (troop_get_inventory_slot_modifier, ":modifier", ":troop", ":slot"),
            (troop_inventory_slot_get_item_amount, ":amount", ":troop", ":slot"),
            (store_mul, ":where", ":side", 1000),
            (val_add, ":where", ":slot"),
            (store_mul, ":extra", ":modifier", 10000),
            (val_add, ":extra", ":amount"),
            (multiplayer_send_4_int_to_server, fc_event, fc_msg_inv_slot, ":where", ":item", ":extra"),
        (try_end),
        (multiplayer_send_3_int_to_server, fc_event, fc_msg_inv_end, ":side", 0),
    ]),

    # The server opens the trade or loot screen.
    ("fc_client_screen_open", [
        (store_script_param, ":kind", 1),
        (store_script_param, ":troop", 2),
        (assign, "$fc_screen_open", ":kind"),
        (try_begin),
            (eq, ":kind", SCREEN_TRADE),
            (change_screen_trade, ":troop"),
        (else_try),
            (change_screen_loot, ":troop"),
        (try_end),
    ]),

    # Back in the remote menu after a screen: send both inventories.
    ("fc_client_screen_done", [
        (gt, "$fc_screen_open", 0),
        (assign, ":kind", "$fc_screen_open"),
        (assign, "$fc_screen_open", 0),
        (assign, "$fc_inv_check", 0),
        (call_script, "script_fc_client_send_inventory", 0, "$fc_inv_troop_0"),
        (call_script, "script_fc_client_send_inventory", 1, "$fc_inv_troop_1"),
        (multiplayer_send_3_int_to_server, fc_event, fc_msg_screen_done, ":kind", 0),
    ]),
]


def _price_override(kind):
    # campaign client: the price factor the server sent for this item (100 if none)
    return [
        (assign, ":fc_price_done", 0),
        (try_begin),
            (multiplayer_is_campaign),
            (neg | multiplayer_is_server),
            (store_script_param_1, ":fc_item"),
            (call_script, "script_fc_client_prices_dict"),
            (assign, reg60, ":fc_item"),
            (str_store_string, s65, "@" + kind + "{reg60}"),
            (dict_get_int, reg0, "$fc_prices_dict", s65, 100),
            (set_trigger_result, reg0),
            (assign, ":fc_price_done", 1),
        (try_end),
        (eq, ":fc_price_done", 0),
    ]


window_opened = [
    # campaign client: after an inventory/party/character window the map sends our inventory (fc_items)
    (try_begin),
        (multiplayer_is_campaign),
        (neg | multiplayer_is_server),
        (assign, "$fc_inv_check", 1),
    (try_end),
]

simple_triggers = [
    # campaign client, on the map although a screen session is open (the screen went back to the map, not to the
    # menu): finish it here, so the server doesn't wait for it (and keep the merchant locked)
    (0, [
        (multiplayer_is_campaign),
        (neg | multiplayer_is_server),
        (gt, "$fc_screen_open", 0),
        (try_begin),
            (call_script, "script_fc_client_screen_done"),
        (try_end),
    ]),
    # campaign client, on the map: an item window was open -> send our inventory
    (0, [
        (multiplayer_is_campaign),
        (neg | multiplayer_is_server),
        (eq, "$fc_inv_check", 1),
        (eq, "$fc_screen_open", 0),
        (gt, "$fc_inv_troop_0", 0),
        (assign, "$fc_inv_check", 0),
        (call_script, "script_fc_client_send_inventory", 0, "$fc_inv_troop_0"),
        (multiplayer_send_3_int_to_server, fc_event, fc_msg_inv_update, 0, 0),
    ]),
]

patches = [
    fp.add("scripts", common_scripts + server_scripts + client_scripts, origin="fc_items"),
    fp.prepend_ops("scripts", "game_get_item_buy_price_factor", _price_override("b"), origin="fc_items"),
    fp.prepend_ops("scripts", "game_get_item_sell_price_factor", _price_override("s"), origin="fc_items"),
    fp.append_ops("scripts", "wse_window_opened", window_opened, origin="fc_items"),
    fp.add("simple_triggers", simple_triggers, origin="fc_items"),
]
