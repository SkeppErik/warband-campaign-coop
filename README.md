# Warband Campaign Co-op

The whole Mount & Blade: Warband single-player campaign in co-op: one shared map, everyone with their own
character and party, and every feature working the way it does in single player. Written from scratch; see
[docs/PLAN.md](docs/PLAN.md) for the plan and where it stands.

> Status: early work. Nothing playable yet.

## How it's built

This repository holds only our own code. The build takes the official pieces you download yourself and applies
our changes on top:

1. TaleWorlds' **Mount&Blade Warband Module System** (official download from taleworlds.com), unpacked as it is.
2. The **WSE2 SDK** (shipped with WSE2), applied the way its README describes.
3. Our code in `src/`: every change to native's scripts, menus, troops and so on is a patch
   (`tools/fcpatch.py`) that must find exactly what it names, so a different module system version stops the
   build instead of breaking quietly.
4. The module system's own build steps, with Python 2.7.

```
python tools/build.py --module-system <module system zip or folder> --wse2-sdk <WSE2 SDK folder>
```

The result is in `build/module`. To try it, install it into a **test copy** of the game (never your real install;
the tool refuses anything inside a Steam library):

```
python tools/install.py --game <test copy of Warband>
```

It creates `Modules/CampaignCoop` from native's own module folder plus the built files. Requirements: Python 2.7 (the module system doesn't run on Python 3; on Windows
the build looks for `C:\Python27\python.exe`, or pass `--py27`).

## Layout

| Path | What's there |
|---|---|
| `src/` | The mod: `fc_*.py` files, each with its patches; `fc_patches.py` lists them all |
| `tools/` | `build.py` (the build), `fcpatch.py` (the patch operations), `install.py` (into a test copy) |
| `tests/` | Tests for the tools: `python tests/test_fcpatch.py`, `python tests/test_build.py` (Python 2.7 or 3) |
| `docs/` | The plan and the design notes |

## License

MIT, see [LICENSE](LICENSE). TaleWorlds' module system and WSE2 are not part of this repository and keep their
own terms.
