"""Every change we make to the module system's lists, in the order they apply (tools/fcpatch.py)."""
import fc_authority
import fc_console
import fc_menus
import fc_net
import fc_players

patches = (
    fc_menus.patches       # first: rewrites only native's code
    + fc_authority.patches # guards only native's triggers
    + fc_net.patches
    + fc_players.patches
    + fc_console.patches
)
