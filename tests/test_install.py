"""Tests for tools/install.py. Run: python tests/test_install.py (Python 2.7 or 3)."""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import install  # noqa: E402


def make(path, text=""):
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "w") as f:
        f.write(text)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.game = os.path.join(self.tmp, "WarbandTest")
        make(os.path.join(self.game, "Modules", "Native", "module.ini"), "native\n")
        make(os.path.join(self.game, "Modules", "Native", "game_variables.txt"), "a = 1\nb = 2\n")
        self.built = os.path.join(self.tmp, "built")
        make(os.path.join(self.built, "scripts.txt"), "scripts\n")
        self.sdk = os.path.join(self.tmp, "sdk")
        make(os.path.join(self.sdk, "game_variables.txt_addon.txt"), "b = 3\n\nc = 4\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_install(self, game=None, sdk=None):
        return install.main(["--game", game or self.game, "--built", self.built, "--wse2-sdk", sdk or self.sdk])

    def test_install(self):
        self.assertEqual(self.run_install(), 0)
        module = os.path.join(self.game, "Modules", "CampaignCoop")
        self.assertTrue(os.path.isfile(os.path.join(module, "scripts.txt")))
        with open(os.path.join(module, "game_variables.txt")) as f:
            self.assertEqual(f.read().split("\n")[:3], ["a = 1", "b = 3", "c = 4"])
        with open(os.path.join(self.game, "Modules", "Native", "game_variables.txt")) as f:
            self.assertEqual(f.read(), "a = 1\nb = 2\n")   # native's own folder is left alone
        self.assertTrue(os.path.isfile(os.path.join(self.game, "fc_server.bat")))
        self.assertTrue(os.path.isfile(os.path.join(module, "module_config_template.ini")))

    def test_refuses_a_steam_library(self):
        steam = os.path.join(self.tmp, "SteamLibrary", "steamapps", "common", "MountBlade Warband")
        shutil.copytree(self.game, steam)
        self.assertEqual(self.run_install(game=steam), 1)
        self.assertFalse(os.path.isdir(os.path.join(steam, "Modules", "CampaignCoop")))

    def test_a_missing_sdk_changes_nothing(self):
        self.assertEqual(self.run_install(sdk=os.path.join(self.tmp, "nope")), 1)
        self.assertFalse(os.path.isdir(os.path.join(self.game, "Modules", "CampaignCoop")))


if __name__ == "__main__":
    unittest.main()
