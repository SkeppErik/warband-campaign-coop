"""Installs the built module into a TEST copy of the game.

    python tools/install.py --game <test copy of Warband> [--built build/module] [--name CampaignCoop]

The module folder is native's own Modules/Native (its resources, textures, sounds, module.ini) with the built
*.txt files on top. Refuses to touch a game inside a Steam library: never install into your real game.
"""
from __future__ import print_function

import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game", required=True, help="the test copy of Warband (never the Steam install)")
    ap.add_argument("--built", default=os.path.join(REPO, "build", "module"), help="tools/build.py output")
    ap.add_argument("--name", default="CampaignCoop", help="module folder name")
    args = ap.parse_args(argv)

    game = os.path.abspath(args.game)
    if "steamapps" in game.lower().replace("\\", "/").split("/"):
        print("REFUSED: %s is inside a Steam library. Install into a test copy of the game." % game)
        return 1
    native = os.path.join(game, "Modules", "Native")
    if not os.path.isfile(os.path.join(native, "module.ini")):
        print("no Modules/Native/module.ini in %s: is this a Warband folder?" % game)
        return 1
    built = os.path.abspath(args.built)
    texts = [n for n in os.listdir(built) if n.endswith(".txt")] if os.path.isdir(built) else []
    if "scripts.txt" not in texts:
        print("no built module in %s (run tools/build.py first)" % built)
        return 1

    target = os.path.join(game, "Modules", args.name)
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(native, target)
    for name in texts:
        shutil.copy(os.path.join(built, name), target)
    print("installed %d files into %s" % (len(texts), target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
