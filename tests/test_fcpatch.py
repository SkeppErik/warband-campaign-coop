"""Tests for tools/fcpatch.py. Run: python tests/test_fcpatch.py (Python 2.7 or 3)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import fcpatch as fp  # noqa: E402

SCRIPTS = [("game_start", [("op", 1)]), ("encounter", [("op", 2)])]
MENUS = [("town", 0, "text", "none", [("menu_op",)], [("trade", [], "Trade", []), ("leave", [], "Leave", [])])]
SIMPLE = [(24, [("daily",)]), (1, [("hourly",)])]


class AddTests(unittest.TestCase):
    def test_add_at_end_start_and_next_to_an_anchor(self):
        new = ("fc_join", [])
        self.assertEqual(fp.apply("scripts", SCRIPTS, [fp.add("scripts", [new])])[-1], new)
        self.assertEqual(fp.apply("scripts", SCRIPTS, [fp.add("scripts", [new], first=True)])[0], new)
        out = fp.apply("scripts", SCRIPTS, [fp.add("scripts", [new], before="encounter")])
        self.assertEqual([fp.entry_id(e) for e in out], ["game_start", "fc_join", "encounter"])
        out = fp.apply("scripts", SCRIPTS, [fp.add("scripts", [new], after="game_start")])
        self.assertEqual([fp.entry_id(e) for e in out], ["game_start", "fc_join", "encounter"])

    def test_add_refuses_an_existing_id_and_a_missing_anchor(self):
        self.assertRaises(fp.PatchError, fp.apply, "scripts", SCRIPTS, [fp.add("scripts", [("encounter", [])])])
        self.assertRaises(fp.PatchError, fp.apply, "scripts", SCRIPTS,
                          [fp.add("scripts", [("x", [])], before="no_such")])

    def test_add_from_copies_native_entries(self):
        copies = lambda entries: [("fc_" + entries[0][0] + "_%d" % i,) + tuple(entries[0][1:]) for i in range(2)]
        out = fp.apply("scripts", SCRIPTS, [fp.add_from("scripts", copies)])
        self.assertEqual([fp.entry_id(e) for e in out][-2:], ["fc_game_start_0", "fc_game_start_1"])
        clash = lambda entries: [entries[1]]
        self.assertRaises(fp.PatchError, fp.apply, "scripts", SCRIPTS, [fp.add_from("scripts", clash)])

    def test_entries_without_ids_can_be_added(self):
        out = fp.apply("simple_triggers", SIMPLE, [fp.add("simple_triggers", [(0, []), (0, [])])])
        self.assertEqual(len(out), 4)


class ChangeTests(unittest.TestCase):
    def test_replace_remove_edit(self):
        out = fp.apply("scripts", SCRIPTS, [fp.replace("scripts", "encounter", ("encounter", [("new",)]))])
        self.assertEqual(out[1], ("encounter", [("new",)]))
        out = fp.apply("scripts", SCRIPTS, [fp.remove("scripts", "game_start")])
        self.assertEqual([fp.entry_id(e) for e in out], ["encounter"])
        out = fp.apply("scripts", SCRIPTS, [fp.edit("scripts", "game_start", lambda e: (e[0], []))])
        self.assertEqual(out[0], ("game_start", []))

    def test_a_missing_or_doubled_id_stops_the_build(self):
        self.assertRaises(fp.PatchError, fp.apply, "scripts", SCRIPTS, [fp.remove("scripts", "nope")])
        doubled = SCRIPTS + [("encounter", [])]
        self.assertRaises(fp.PatchError, fp.apply, "scripts", doubled, [fp.remove("scripts", "encounter")])

    def test_replace_must_keep_the_id(self):
        self.assertRaises(fp.PatchError, fp.apply, "scripts", SCRIPTS,
                          [fp.replace("scripts", "encounter", ("other", []))])

    def test_ops_go_to_the_start_or_end(self):
        out = fp.apply("scripts", SCRIPTS, [fp.prepend_ops("scripts", "encounter", [("first",)]),
                                            fp.append_ops("scripts", "encounter", [("last",)])])
        self.assertEqual(out[1][1], [("first",), ("op", 2), ("last",)])
        out = fp.apply("game_menus", MENUS, [fp.prepend_ops("game_menus", "town", [("gate",)])])
        self.assertEqual(out[0][4], [("gate",), ("menu_op",)])

    def test_the_native_list_is_left_alone(self):
        fp.apply("scripts", SCRIPTS, [fp.append_ops("scripts", "encounter", [("x",)])])
        self.assertEqual(SCRIPTS[1], ("encounter", [("op", 2)]))

    def test_patches_for_other_lists_are_skipped(self):
        out = fp.apply("scripts", SCRIPTS, [fp.add("game_menus", [("m", 0, "", "none", [], [])])])
        self.assertEqual(out, SCRIPTS)


class SimpleTriggerTests(unittest.TestCase):
    def test_edit_by_index_checks_the_interval(self):
        out = fp.apply("simple_triggers", SIMPLE,
                       [fp.edit_simple_trigger(1, lambda t: (t[0], [("gate",)] + t[1]), interval=1)])
        self.assertEqual(out[1][1], [("gate",), ("hourly",)])
        self.assertRaises(fp.PatchError, fp.apply, "simple_triggers", SIMPLE,
                          [fp.edit_simple_trigger(1, lambda t: t, interval=24)])


class MenuTests(unittest.TestCase):
    def test_options(self):
        opt = ("fc_wait", [], "Wait", [])
        out = fp.apply("game_menus", MENUS, [fp.add_menu_option("town", opt, before="leave")])
        self.assertEqual([o[0] for o in out[0][5]], ["trade", "fc_wait", "leave"])
        out = fp.apply("game_menus", MENUS, [fp.remove_menu_option("town", "trade")])
        self.assertEqual([o[0] for o in out[0][5]], ["leave"])
        out = fp.apply("game_menus", MENUS, [fp.replace_menu_option("town", "leave", ("leave", [], "Go", []))])
        self.assertEqual(out[0][5][1][2], "Go")
        out = fp.apply("game_menus", MENUS, [fp.edit_menu_option("town", "trade", lambda o: o[:2] + ("Buy",) + o[3:])])
        self.assertEqual(out[0][5][0][2], "Buy")
        self.assertRaises(fp.PatchError, fp.apply, "game_menus", MENUS, [fp.remove_menu_option("town", "nope")])
        self.assertRaises(fp.PatchError, fp.apply, "game_menus", MENUS, [fp.add_menu_option("town", opt[:0] + ("trade", [], "", []))])


class NestedTests(unittest.TestCase):
    def test_mission_and_presentation_triggers(self):
        templates = [("battle", 0, -1, "desc", [], [("t1",)])]
        out = fp.apply("mission_templates", templates, [fp.add_mission_triggers("battle", [("t2",)])])
        self.assertEqual(out[0][5], [("t1",), ("t2",)])
        prsnt = [("map", 0, 0, [("p1",)])]
        out = fp.apply("presentations", prsnt, [fp.add_presentation_triggers("map", [("p2",)])])
        self.assertEqual(out[0][3], [("p1",), ("p2",)])


if __name__ == "__main__":
    unittest.main()
