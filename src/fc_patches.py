"""Every change we make to the module system's lists, in the order they apply (tools/fcpatch.py)."""
import fc_join
import fc_net
import fc_players

patches = (
    fc_net.patches
    + fc_players.patches
    + fc_join.patches
)
