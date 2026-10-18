import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import layout  # noqa: E402

SELF = "io.github.bryanperdana.bar-collapse"


def fixture():
    with open(os.path.join(HERE, "fixture_shell.json")) as f:
        config = json.load(f)
    config["bar"]["layout"]["right"].insert(0, {
        "id": SELF,
        "hidden": ["netmojo.omdrop", "meviusisback.hw-monitor"],
        "stash": [],
        "expanded": True,
    })
    return config


def ids(config, section="right"):
    return [e["id"] for e in config["bar"]["layout"][section]]


def self_entry(config):
    return next(e for e in config["bar"]["layout"]["right"] if e["id"] == SELF)


class CoreTest(unittest.TestCase):
    def test_collapse_moves_hidden_to_stash(self):
        out = layout.collapse(fixture(), SELF)
        self.assertNotIn("netmojo.omdrop", ids(out))
        self.assertNotIn("meviusisback.hw-monitor", ids(out))
        entry = self_entry(out)
        self.assertEqual(entry["stash"][1], {"id": "meviusisback.hw-monitor", "mode": "compact"})
        self.assertFalse(entry["expanded"])

    def test_collapse_does_not_mutate_input(self):
        original = fixture()
        snapshot = copy.deepcopy(original)
        layout.collapse(original, SELF)
        self.assertEqual(original, snapshot)

    def test_expand_inserts_before_self(self):
        out = layout.expand(layout.collapse(fixture(), SELF), SELF, None)
        self.assertEqual(ids(out)[0:3], ["netmojo.omdrop", "meviusisback.hw-monitor", SELF])
        self.assertEqual(self_entry(out)["stash"], [])
        self.assertTrue(self_entry(out)["expanded"])

    def test_collapse_idempotent(self):
        once = layout.collapse(fixture(), SELF)
        self.assertEqual(layout.collapse(once, SELF), once)

    def test_expand_idempotent(self):
        once = layout.expand(layout.collapse(fixture(), SELF), SELF, None)
        self.assertEqual(layout.expand(once, SELF, None), once)

    def test_toggle_roundtrip_restores_order(self):
        start = layout.expand(layout.collapse(fixture(), SELF), SELF, None)
        twice = layout.toggle(layout.toggle(start, SELF, None), SELF, None)
        self.assertEqual(twice, start)

    def test_preserves_unrelated(self):
        start = fixture()
        out = layout.collapse(start, SELF)
        for key in ("idle", "plugins", "disabledPlugins", "version"):
            self.assertEqual(out[key], start[key])
        self.assertEqual(out["bar"]["centerAnchor"], start["bar"]["centerAnchor"])
        self.assertEqual(out["bar"]["layout"]["center"], start["bar"]["layout"]["center"])
        clock = next(e for e in out["bar"]["layout"]["center"] if e["id"] == "omarchy.clock")
        self.assertEqual(clock["format"], "dddd HH:mm")

    def test_expand_skips_uninstalled_keeps_stash(self):
        collapsed = layout.collapse(fixture(), SELF)
        installed = {"meviusisback.hw-monitor"}
        out = layout.expand(collapsed, SELF, installed)
        self.assertNotIn("netmojo.omdrop", ids(out))
        self.assertIn("meviusisback.hw-monitor", ids(out))
        self.assertEqual([e["id"] for e in self_entry(out)["stash"]], ["netmojo.omdrop"])

    def test_missing_self_is_noop(self):
        config = fixture()
        config["bar"]["layout"]["right"].pop(0)
        self.assertEqual(layout.collapse(config, SELF), config)
        self.assertEqual(layout.expand(config, SELF, None), config)
        self.assertIsNone(layout.find_self(config, SELF))

    def test_find_self(self):
        self.assertEqual(layout.find_self(fixture(), SELF), ("right", 0))


class HiddenTest(unittest.TestCase):
    def test_unhide_while_collapsed_goes_after_self(self):
        collapsed = layout.collapse(fixture(), SELF)
        out = layout.set_hidden(collapsed, SELF, "netmojo.omdrop", False)
        right = ids(out)
        self.assertEqual(right[right.index(SELF) + 1], "netmojo.omdrop")
        self.assertNotIn("netmojo.omdrop", self_entry(out)["hidden"])
        self.assertEqual([e["id"] for e in self_entry(out)["stash"]], ["meviusisback.hw-monitor"])

    def test_hide_while_collapsed_moves_to_stash(self):
        collapsed = layout.collapse(fixture(), SELF)
        out = layout.set_hidden(collapsed, SELF, "omarchy.agents", True)
        self.assertNotIn("omarchy.agents", ids(out))
        self.assertEqual(self_entry(out)["stash"][-1], {"id": "omarchy.agents"})

    def test_hide_while_expanded_only_updates_list(self):
        start = fixture()
        out = layout.set_hidden(start, SELF, "omarchy.agents", True)
        self.assertEqual(ids(out), ids(start))
        self.assertIn("omarchy.agents", self_entry(out)["hidden"])

    def test_set_hidden_ignores_self(self):
        start = fixture()
        self.assertEqual(layout.set_hidden(start, SELF, SELF, True), start)

    def test_candidates_order(self):
        collapsed = layout.collapse(fixture(), SELF)
        got = layout.candidates(collapsed, SELF)
        self.assertEqual(got[0], {"id": "netmojo.omdrop", "hidden": True})
        self.assertEqual(got[1], {"id": "meviusisback.hw-monitor", "hidden": True})
        self.assertIn({"id": "omarchy.tray", "hidden": False}, got)
        self.assertNotIn(SELF, [c["id"] for c in got])

    def test_restore_removes_self_and_returns_everything(self):
        collapsed = layout.collapse(fixture(), SELF)
        out = layout.restore(collapsed, SELF)
        self.assertIsNone(layout.find_self(out, SELF))
        self.assertIn("netmojo.omdrop", ids(out))
        self.assertIn("meviusisback.hw-monitor", ids(out))


class CliTest(unittest.TestCase):
    def run_cli(self, path, *args):
        import subprocess
        return subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(HERE), "layout.py"), "--config", path, "--no-installed", *args],
            capture_output=True, text=True, check=True)

    def test_cli_toggle_roundtrip(self):
        import tempfile
        start = layout.expand(layout.collapse(fixture(), SELF), SELF, None)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "shell.json")
            with open(path, "w") as f:
                json.dump(start, f, indent=2)
            self.run_cli(path, "toggle")
            with open(path) as f:
                self.assertNotIn("netmojo.omdrop", ids(json.load(f)))
            self.run_cli(path, "toggle")
            with open(path) as f:
                self.assertEqual(json.load(f), start)

    def test_cli_list_prints_candidates(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "shell.json")
            with open(path, "w") as f:
                json.dump(fixture(), f)
            out = self.run_cli(path, "list")
            self.assertEqual(json.loads(out.stdout), layout.candidates(fixture(), SELF))

    def test_cli_unchanged_file_not_rewritten(self):
        import tempfile
        config = fixture()
        config["bar"]["layout"]["right"].pop(0)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "shell.json")
            with open(path, "w") as f:
                json.dump(config, f)
                f.write("\n\n")
            self.run_cli(path, "toggle")
            with open(path) as f:
                self.assertTrue(f.read().endswith("\n\n"))


class ReviewFixTest(unittest.TestCase):
    def multi(self):
        config = fixture()
        right = config["bar"]["layout"]["right"]
        right.insert(1, {"id": "meviusisback.hw-monitor", "mode": "cpu"})
        return config

    def test_collapse_keeps_every_instance_of_a_multi_widget(self):
        collapsed = layout.collapse(self.multi(), SELF)
        hw = [e for e in self_entry(collapsed)["stash"] if e["id"] == "meviusisback.hw-monitor"]
        self.assertEqual([e["mode"] for e in hw], ["cpu", "compact"])

    def test_expand_restores_every_instance(self):
        out = layout.expand(layout.collapse(self.multi(), SELF), SELF, None)
        modes = [e.get("mode") for e in out["bar"]["layout"]["right"] if e["id"] == "meviusisback.hw-monitor"]
        self.assertEqual(modes, ["cpu", "compact"])

    def test_show_restores_every_instance(self):
        collapsed = layout.collapse(self.multi(), SELF)
        out = layout.set_hidden(collapsed, SELF, "meviusisback.hw-monitor", False)
        self.assertEqual(ids(out).count("meviusisback.hw-monitor"), 2)
        self.assertEqual([e["id"] for e in self_entry(out)["stash"]], ["netmojo.omdrop"])

    def test_write_atomic_keeps_symlink_and_mode(self):
        import stat
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            real = os.path.join(tmp, "dotfiles-shell.json")
            link = os.path.join(tmp, "shell.json")
            with open(real, "w") as f:
                f.write("{}")
            os.chmod(real, 0o644)
            os.symlink(real, link)
            layout.write_atomic(link, {"a": 1})
            self.assertTrue(os.path.islink(link))
            with open(real) as f:
                self.assertEqual(json.load(f), {"a": 1})
            self.assertEqual(stat.S_IMODE(os.stat(real).st_mode), 0o644)


if __name__ == "__main__":
    unittest.main()
