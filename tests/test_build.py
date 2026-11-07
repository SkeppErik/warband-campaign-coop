"""Tests for tools/build.py against a small fake module system and WSE2 SDK.

The fake has the official one's shape (list files, headers, process_*.py, build_module.bat), so the staging,
the WSE2 SDK edits, the wrappers and the module system's step runner are all exercised.
Run: python tests/test_build.py (Python 2.7 or 3).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import build  # noqa: E402

FAKE_MS = {
    "module_info.py": 'export_dir = "../WOTS/Modules/Native/"\n',
    "header_common.py": "reg0 = 72057594037927936\n",
    "header_operations.py": "display_message = 1104\nlhs_operations = []\ncan_fail_operations = []\n",
    "module_constants.py": "slot_native = 1\n",
    "module_scripts.py": 'from header_operations import *\nscripts = [("game_start", [(display_message, "@hi")])]\n',
    "module_troops.py": 'troops = [("player", "Player", "Player", 0)]\n',
    "process_init.py": "print('init done')\n",
    "process_scripts.py": textwrap.dedent('''\
        from module_scripts import scripts
        from module_info import export_dir
        with open(export_dir + "scripts.txt", "w") as f:
            for s in scripts:
                f.write(s[0] + "\\n")
        print("scripts done")
        '''),
    "process_operations.py": textwrap.dedent('''\
        def x(opcode):
            if (opcode in [try_begin,
                           try_for_range,
                           try_for_range_backwards,
                           try_for_parties,
                           try_for_agents]):
              return 1
        '''),
    "process_skins.py": "def save(skins):\n  if len(skins) > 16:\n    skins = skins[0:15]\n  return skins\n",
    "build_module.bat": "python process_init.py\npython process_scripts.py\n@pause\n",
}

FAKE_SDK = {
    "header_operations_addon.py": "store_random = 2135\nlhs_operations += [store_random]\n",
    "module_scripts_addon.py": '("wse_game_saved", [\n]),\n',
    "README.txt": "add the addons\n",
}

OUR_SRC = {
    "fc_constants.py": "fc_answer = 42\n",
    "fc_patches.py": textwrap.dedent('''\
        import fcpatch as fp
        from header_operations import *
        patches = [
            fp.add("scripts", [("fc_hello", [(display_message, "@hello")])]),
            fp.add_from("troops", lambda t: [("fc_" + t[0][0],) + tuple(t[0][1:])]),
        ]
        '''),
}


def make(folder, files):
    os.makedirs(folder)
    for name, text in files.items():
        with open(os.path.join(folder, name), "w") as f:
            f.write(text)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ms = os.path.join(self.tmp, "Module_system 1171", "Module_system 1171")
        make(self.ms, FAKE_MS)
        self.sdk = os.path.join(self.tmp, "sdk")
        make(self.sdk, FAKE_SDK)
        self.src = os.path.join(self.tmp, "oursrc")
        make(self.src, OUR_SRC)
        self.out = os.path.join(self.tmp, "out")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_build(self, *extra):
        args = ["--module-system", os.path.dirname(self.ms), "--wse2-sdk", self.sdk, "--src", self.src,
                "--out", self.out, "--py27", sys.executable] + list(extra)
        return build.main(args)

    def staged(self, name):
        with open(os.path.join(self.out, "src", name)) as f:
            return f.read()

    def test_full_build(self):
        self.assertEqual(self.run_build(), 0)
        with open(os.path.join(self.out, "module", "scripts.txt")) as f:
            self.assertEqual(f.read().split(), ["game_start", "wse_game_saved", "fc_hello"])

    def test_staging(self):
        self.assertEqual(self.run_build("--stage-only"), 0)
        self.assertIn("try_for_agents, try_for_prop_instances, try_for_players, try_for_dict_keys",
                      self.staged("process_operations.py"))
        self.assertNotIn("len(skins) > 16", self.staged("process_skins.py"))
        self.assertIn("store_random = 2135", self.staged("header_operations.py"))
        self.assertIn("from fc_constants import *", self.staged("module_constants.py"))
        self.assertIn(os.path.join(self.out, "module").replace("\\", "/"), self.staged("module_info.py"))
        # the wrapped lists, loaded the way the module system's steps load them
        code = ("import module_troops, module_scripts, module_constants; "
                "print([t[0] for t in module_troops.troops]); print(module_constants.fc_answer)")
        out = subprocess.check_output([sys.executable, "-c", code], cwd=os.path.join(self.out, "src"))
        self.assertEqual(out.decode().splitlines()[:2], ["['player', 'fc_player']", "42"])

    def test_a_different_module_system_version_stops_the_build(self):
        with open(os.path.join(self.ms, "process_skins.py"), "w") as f:
            f.write("def save(skins):\n  return skins\n")
        self.assertEqual(self.run_build("--stage-only"), 1)

    def test_a_failing_step_stops_the_build(self):
        with open(os.path.join(self.ms, "process_init.py"), "w") as f:
            f.write("print('ERROR: something')\n")
        self.assertEqual(self.run_build(), 1)


if __name__ == "__main__":
    unittest.main()
