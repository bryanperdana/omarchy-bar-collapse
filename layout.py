#!/usr/bin/env python3
"""Collapse and expand bar widgets by rewriting ~/.config/omarchy/shell.json.

Only `bar`-kind plugins may mutate the bar layout from inside the shell, so the
Bar Collapse widget hands every change to this helper. State lives on the
plugin's own bar entry:

    {"id": "io.github.bryanperdana.bar-collapse", "hidden": [ids], "stash": [entries], "expanded": bool}

`stash` keeps the full entries (with their settings) of hidden widgets while
the bar is collapsed, in bar order. Every function returns a new config and
leaves its input untouched.
"""
import copy

SECTIONS = ("left", "center", "right")


def _sections(config):
    layout = config.get("bar", {}).get("layout", {})
    return {name: layout[name] for name in SECTIONS if isinstance(layout.get(name), list)}


def find_self(config, self_id):
    for name, entries in _sections(config).items():
        for index, entry in enumerate(entries):
            if isinstance(entry, dict) and entry.get("id") == self_id:
                return name, index
    return None


def _self_entry(config, self_id):
    found = find_self(config, self_id)
    if found is None:
        return None, None
    name, index = found
    return config["bar"]["layout"][name], config["bar"]["layout"][name][index]


def collapse(config, self_id):
    config = copy.deepcopy(config)
    section, entry = _self_entry(config, self_id)
    if entry is None:
        return config
    hidden = set(entry.get("hidden") or [])
    stash = [e for e in entry.get("stash") or [] if isinstance(e, dict)]
    keep = []
    for item in section:
        item_id = item.get("id") if isinstance(item, dict) else None
        if item_id in hidden and item_id != self_id:
            # Widgets with allowMultiple share an id, so every entry is kept.
            stash.append(item)
        else:
            keep.append(item)
    section[:] = keep
    entry["stash"] = stash
    entry["expanded"] = False
    return config


def expand(config, self_id, installed):
    config = copy.deepcopy(config)
    section, entry = _self_entry(config, self_id)
    if entry is None:
        return config
    insert, remaining = [], []
    for item in entry.get("stash") or []:
        if not isinstance(item, dict):
            continue
        if installed is not None and item.get("id") not in installed:
            remaining.append(item)
            continue
        insert.append(item)
    index = section.index(entry)
    section[index:index] = insert
    entry["stash"] = remaining
    entry["expanded"] = True
    return config


def toggle(config, self_id, installed):
    _, entry = _self_entry(config, self_id)
    if entry is None:
        return copy.deepcopy(config)
    if entry.get("expanded", True):
        return collapse(config, self_id)
    return expand(config, self_id, installed)


def set_hidden(config, self_id, widget_id, hidden):
    config = copy.deepcopy(config)
    section, entry = _self_entry(config, self_id)
    if entry is None or widget_id == self_id:
        return config
    ids = [i for i in entry.get("hidden") or [] if i != widget_id]
    if hidden:
        ids.append(widget_id)
    entry["hidden"] = ids
    if entry.get("expanded", True):
        return config
    stash = [e for e in entry.get("stash") or [] if isinstance(e, dict)]
    if hidden:
        for item in list(section):
            if isinstance(item, dict) and item.get("id") == widget_id:
                section.remove(item)
                stash.append(item)
    else:
        back = [e for e in stash if e.get("id") == widget_id]
        stash = [e for e in stash if e.get("id") != widget_id]
        index = section.index(entry)
        section[index + 1:index + 1] = back
    entry["stash"] = stash
    return config


def candidates(config, self_id):
    section, entry = _self_entry(config, self_id)
    if entry is None:
        return []
    hidden = set(entry.get("hidden") or [])
    result, seen = [], set()
    for item in (entry.get("stash") or []) + section:
        item_id = item.get("id") if isinstance(item, dict) else None
        if not item_id or item_id == self_id or item_id in seen:
            continue
        seen.add(item_id)
        result.append({"id": item_id, "hidden": item_id in hidden})
    return result


def restore(config, self_id):
    expanded = expand(config, self_id, None)
    section, entry = _self_entry(expanded, self_id)
    if entry is not None:
        section.remove(entry)
    return expanded


def installed_ids():
    import json
    import subprocess
    try:
        out = subprocess.run(["omarchy", "plugin", "list", "--json"],
                             capture_output=True, text=True, timeout=10, check=True).stdout
        data = json.loads(out)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    rows = data.get("plugins", data) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return None
    return {str(r.get("id")) for r in rows if isinstance(r, dict) and r.get("id")}


def write_atomic(path, config):
    import json
    import os
    import tempfile
    # Write through a symlink (dotfiles setups) and keep the file's mode.
    target = os.path.realpath(path)
    directory = os.path.dirname(target)
    try:
        mode = os.stat(target).st_mode & 0o7777
    except OSError:
        mode = 0o644
    with tempfile.NamedTemporaryFile("w", dir=directory, delete=False, suffix=".tmp") as tmp:
        json.dump(config, tmp, indent=2, ensure_ascii=False)
        tmp.write("\n")
        name = tmp.name
    os.chmod(name, mode)
    os.replace(name, target)


def main(argv=None):
    import argparse
    import json
    import os
    import sys
    parser = argparse.ArgumentParser(description="Bar Collapse layout helper")
    parser.add_argument("--config", default=os.path.expanduser("~/.config/omarchy/shell.json"))
    parser.add_argument("--self", dest="self_id", default="io.github.bryanperdana.bar-collapse")
    parser.add_argument("--no-installed", action="store_true", help="skip the installed-plugin filter")
    parser.add_argument("command", choices=["toggle", "hide", "show", "list", "restore"])
    parser.add_argument("widget", nargs="?")
    args = parser.parse_args(argv)

    with open(args.config) as f:
        config = json.load(f)

    if args.command == "list":
        json.dump(candidates(config, args.self_id), sys.stdout)
        sys.stdout.write("\n")
        return 0
    if find_self(config, args.self_id) is None:
        print("bar-collapse: %s is not on the bar" % args.self_id, file=sys.stderr)
        return 0
    if args.command in ("hide", "show") and not args.widget:
        parser.error("%s needs a widget id" % args.command)

    installed = None if args.no_installed else installed_ids()
    if args.command == "toggle":
        updated = toggle(config, args.self_id, installed)
    elif args.command == "hide":
        updated = set_hidden(config, args.self_id, args.widget, True)
    elif args.command == "show":
        updated = set_hidden(config, args.self_id, args.widget, False)
    else:
        updated = restore(config, args.self_id)

    if updated != config:
        write_atomic(args.config, updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
