# Build inputs

The official files the build uses. None of them is in this repository; download them yourself and check the
SHA-256 before building. `tools/build.py` writes what it actually used to `build/inputs.txt`.

| Input | Source | Version | SHA-256 |
|---|---|---|---|
| Mount&Blade Warband Module System | http://download.taleworlds.com/mb_warband_module_system_1171.zip (TaleWorlds, linked from the forum's "Warband Modder's Download Repository") | 1.171 (zip dated 2016-12-23) | `b8d5095031ed2b9df0a4020097bea06b6137022a52cd24a9d5c6b575444b16e1` |
| WSE2 (its `WSE2 SDK` folder) | K700's thread on the TaleWorlds forum | not recorded yet | not recorded yet |

Native 1.171's highest slot number is 500 (a town slot); our `fc_slot_*` constants must stay above it (checked by
the build).
