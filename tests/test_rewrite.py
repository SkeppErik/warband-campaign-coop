"""Tests for src/fc_rewrite.py. Run: python tests/test_rewrite.py (Python 2.7 or 3)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import fc_rewrite as rw  # noqa: E402

CALL = 1
JUMP = 2060
RETURN = 2040
NEG = 0x80000000
ASSIGN = 2133


class RewriteTests(unittest.TestCase):
    def setUp(self):
        self.replace = {JUMP: lambda n: "script_fc_op_jump_to_menu_%d" % n,
                        RETURN: lambda n: "script_fc_op_change_screen_return_%d" % n}
        self.rename = {"p_main_party": "$fc_main_party", "trp_player": "$fc_player_troop"}

    def run_block(self, block):
        return rw.rewrite_block(block, self.replace, self.rename, CALL)

    def test_menu_ops_become_script_calls_with_their_arguments(self):
        out = self.run_block([(JUMP, "mnu_town"), RETURN, (RETURN,)])
        self.assertEqual(out, [(CALL, "script_fc_op_jump_to_menu_1", "mnu_town"),
                               (CALL, "script_fc_op_change_screen_return_0"),
                               (CALL, "script_fc_op_change_screen_return_0")])

    def test_main_party_and_player_troop_are_renamed_everywhere(self):
        out = self.run_block([(ASSIGN, ":x", "p_main_party"), (JUMP, "trp_player"), 3])
        self.assertEqual(out, [(ASSIGN, ":x", "$fc_main_party"),
                               (CALL, "script_fc_op_jump_to_menu_1", "$fc_player_troop"), 3])

    def test_ops_with_modifiers_and_other_strings_are_left_alone(self):
        block = [(JUMP | NEG, "mnu_town"), (ASSIGN, ":p_main_party", "p_main_party_backup")]
        self.assertEqual(self.run_block(block), block)

    def test_written_globals(self):
        block = [(ASSIGN, "$g_a", 1), (ASSIGN | NEG, "$g_b", 1), (ASSIGN, ":local", 1), (JUMP, "$g_c"),
                 (ASSIGN, "$g_a", 2)]
        self.assertEqual(rw.written_globals(block, set([ASSIGN])), ["g_a", "g_b"])


if __name__ == "__main__":
    unittest.main()
