"""Applies our changes to the module system's lists at build time.

The repository holds no TaleWorlds files. tools/build.py unpacks the official module system, and each list file
it changes (module_scripts.py and so on) is replaced by a small wrapper that loads the native list and passes it
through apply() with the patches from src/. A patch names its target list and says what to do: add entries,
replace or remove one by id, edit one with a function, or put operations into a script or menu.

Every patch must find what it names, exactly once: a renamed or missing native entry stops the build instead of
quietly doing nothing.

Runs on Python 2.7 (the module system's interpreter) and on Python 3 (the tests).
"""

# module file -> the list it defines
LISTS = {
    "module_scripts": "scripts",
    "module_game_menus": "game_menus",
    "module_simple_triggers": "simple_triggers",
    "module_triggers": "triggers",
    "module_mission_templates": "mission_templates",
    "module_presentations": "presentations",
    "module_dialogs": "dialogs",
    "module_parties": "parties",
    "module_troops": "troops",
    "module_strings": "strings",
    "module_quests": "quests",
    "module_items": "items",
    "module_party_templates": "party_templates",
    "module_scenes": "scenes",
    "module_factions": "factions",
    "module_info_pages": "info_pages",
}

# where an entry keeps its operation block
OPS_FIELD = {
    "scripts": 1,         # (id, ops)
    "game_menus": 4,      # (id, flags, text, mesh, ops, options)
    "simple_triggers": 1, # (interval, ops)
}
MENU_OPTIONS_FIELD = 5
MISSION_TRIGGERS_FIELD = 5   # (id, flags, type, description, spawn records, triggers)
PRESENTATION_TRIGGERS_FIELD = 3  # (id, flags, mesh, triggers)


class PatchError(Exception):
    pass


def entry_id(entry):
    """The string id an entry starts with, or None (simple triggers, dialogs)."""
    if isinstance(entry, (tuple, list)) and entry and isinstance(entry[0], str):
        return entry[0]
    return None


class Patch(object):
    def __init__(self, target, kind, **args):
        self.target = target
        self.kind = kind
        self.args = args
        self.origin = args.pop("origin", "")

    def describe(self):
        what = self.args.get("id", self.args.get("index", ""))
        return "%s %s %s%s" % (self.kind, self.target, what, " (%s)" % self.origin if self.origin else "")


# ----------------------------------------------------------------------------- patch constructors

def add(target, entries, before=None, after=None, first=False, origin=""):
    """Adds entries at the end, at the start (first=True), or next to the entry with id before / after."""
    return Patch(target, "add", entries=list(entries), before=before, after=after, first=first, origin=origin)


def add_from(target, fn, origin=""):
    """Adds the entries fn(native list) returns at the end (e.g. copies of a native troop)."""
    return Patch(target, "add_from", fn=fn, origin=origin)


def replace(target, id, entry, origin=""):
    return Patch(target, "replace", id=id, entry=entry, origin=origin)


def remove(target, id, origin=""):
    return Patch(target, "remove", id=id, origin=origin)


def edit(target, id, fn, origin=""):
    """fn(entry) returns the new entry."""
    return Patch(target, "edit", id=id, fn=fn, origin=origin)


def prepend_ops(target, id, ops, origin=""):
    """Puts operations at the start of a script's or menu's operation block."""
    return Patch(target, "ops", id=id, ops=list(ops), where="start", origin=origin)


def append_ops(target, id, ops, origin=""):
    return Patch(target, "ops", id=id, ops=list(ops), where="end", origin=origin)


def edit_all(target, fn, origin=""):
    """fn(entry) -> entry for every entry the list has at that point (put it first to touch only native's)."""
    return Patch(target, "edit_all", fn=fn, origin=origin)


def edit_simple_trigger(index, fn, interval, origin=""):
    """Simple triggers have no ids: index into the native list, checked against its interval."""
    return Patch("simple_triggers", "edit_index", index=index, fn=fn, interval=interval, origin=origin)


def add_menu_option(menu, option, before=None, after=None, first=False, origin=""):
    return Patch("game_menus", "menu_add", id=menu, option=option, before=before, after=after, first=first,
                 origin=origin)


def replace_menu_option(menu, option_id, option, origin=""):
    return Patch("game_menus", "menu_replace", id=menu, option_id=option_id, option=option, origin=origin)


def edit_menu_option(menu, option_id, fn, origin=""):
    return Patch("game_menus", "menu_edit", id=menu, option_id=option_id, fn=fn, origin=origin)


def remove_menu_option(menu, option_id, origin=""):
    return Patch("game_menus", "menu_remove", id=menu, option_id=option_id, origin=origin)


def add_mission_triggers(template, triggers, origin=""):
    return Patch("mission_templates", "nested_add", id=template, items=list(triggers),
                 field=MISSION_TRIGGERS_FIELD, origin=origin)


def add_presentation_triggers(presentation, triggers, origin=""):
    return Patch("presentations", "nested_add", id=presentation, items=list(triggers),
                 field=PRESENTATION_TRIGGERS_FIELD, origin=origin)


# ----------------------------------------------------------------------------- applying

def _index_of(entries, id, patch):
    found = [i for i, e in enumerate(entries) if entry_id(e) == id]
    if len(found) != 1:
        raise PatchError("%s: %s entry with id %r" % (patch.describe(), "no" if not found else "more than one", id))
    return found[0]


def _with_field(entry, field, value):
    """A copy of entry with one field changed, of the same type (native troops are lists, most others tuples)."""
    items = list(entry)
    if field >= len(items):
        raise PatchError("entry %r has no field %d" % (entry_id(entry), field))
    items[field] = value
    return type(entry)(items)


def _insert(items, new, before, after, first, patch, id_of=entry_id):
    if sum(1 for x in (before, after, first) if x) > 1:
        raise PatchError("%s: give only one of before, after, first" % patch.describe())
    if first:
        return list(new) + items
    if before or after:
        anchor = before or after
        found = [i for i, e in enumerate(items) if id_of(e) == anchor]
        if len(found) != 1:
            raise PatchError("%s: anchor %r found %d times" % (patch.describe(), anchor, len(found)))
        at = found[0] + (0 if before else 1)
        return items[:at] + list(new) + items[at:]
    return items + list(new)


def _check_new_ids(items, new, patch, id_of=entry_id):
    have = set(id_of(e) for e in items)
    for e in new:
        i = id_of(e)
        if i is not None and i in have:
            raise PatchError("%s: id %r already exists" % (patch.describe(), i))
        have.add(i)


def _option_id(option):
    return option[0] if option and isinstance(option[0], str) else None


def apply_one(entries, p):
    kind = p.kind
    if kind == "add":
        _check_new_ids(entries, p.args["entries"], p)
        return _insert(entries, p.args["entries"], p.args["before"], p.args["after"], p.args["first"], p)
    if kind == "add_from":
        new = list(p.args["fn"](list(entries)))
        _check_new_ids(entries, new, p)
        return list(entries) + new
    if kind == "edit_all":
        if not entries:
            raise PatchError("%s: the list is empty" % p.describe())
        return [p.args["fn"](e) for e in entries]
    if kind == "edit_index":
        i = p.args["index"]
        if i >= len(entries) or entries[i][0] != p.args["interval"]:
            raise PatchError("%s: native simple trigger %d is not the expected one (interval %r)"
                             % (p.describe(), i, p.args["interval"]))
        out = list(entries)
        out[i] = p.args["fn"](entries[i])
        return out

    i = _index_of(entries, p.args["id"], p)
    out = list(entries)
    entry = entries[i]
    if kind == "replace":
        if entry_id(p.args["entry"]) != p.args["id"]:
            raise PatchError("%s: the new entry has id %r" % (p.describe(), entry_id(p.args["entry"])))
        out[i] = p.args["entry"]
    elif kind == "remove":
        del out[i]
    elif kind == "edit":
        out[i] = p.args["fn"](entry)
    elif kind == "ops":
        field = OPS_FIELD.get(p.target)
        if field is None:
            raise PatchError("%s: no operation block known for %s" % (p.describe(), p.target))
        ops = list(entry[field])
        ops = p.args["ops"] + ops if p.args["where"] == "start" else ops + p.args["ops"]
        out[i] = _with_field(entry, field, ops)
    elif kind == "nested_add":
        field = p.args["field"]
        out[i] = _with_field(entry, field, list(entry[field]) + p.args["items"])
    elif kind.startswith("menu_"):
        options = list(entry[MENU_OPTIONS_FIELD])
        if kind == "menu_add":
            _check_new_ids(options, [p.args["option"]], p, _option_id)
            options = _insert(options, [p.args["option"]], p.args["before"], p.args["after"], p.args["first"], p,
                              _option_id)
        else:
            found = [k for k, o in enumerate(options) if _option_id(o) == p.args["option_id"]]
            if len(found) != 1:
                raise PatchError("%s: option %r found %d times" % (p.describe(), p.args["option_id"], len(found)))
            k = found[0]
            if kind == "menu_replace":
                options[k] = p.args["option"]
            elif kind == "menu_edit":
                options[k] = p.args["fn"](options[k])
            elif kind == "menu_remove":
                del options[k]
            else:
                raise PatchError("unknown patch kind %r" % kind)
        out[i] = _with_field(entry, MENU_OPTIONS_FIELD, options)
    else:
        raise PatchError("unknown patch kind %r" % kind)
    return out


def apply(target, entries, patches):
    """Returns the target list with every patch for it applied, in the order given."""
    out = list(entries)
    for p in patches:
        if p.target == target:
            out = apply_one(out, p)
    return out


def targets(patches):
    return sorted(set(p.target for p in patches))
