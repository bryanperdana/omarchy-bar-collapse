# Bar Collapse

A Bartender-style arrow for the [Omarchy](https://omarchy.org) bar. Hide the
widgets you rarely look at behind one click and keep the bar short.

![Bar Collapse](preview.png)

## Usage

- **Left click** the arrow to hide or reveal the hidden widgets. They come back
  just to the left of the arrow.
- **Right click** the arrow for a list of the widgets in its bar section, with a
  switch to mark each one hidden.

Widgets you have never marked stay visible, including ones you install later.
Widgets that allow several instances (for example two hardware monitors) keep
every instance and its settings.

## Install

```bash
omarchy plugin add https://github.com/bryanperdana/omarchy-bar-collapse
omarchy bar put io.github.bryanperdana.bar-collapse --section right --index 0
```

Requires `python3` (shipped with Omarchy).

## How it works

Omarchy only lets bar plugins change the bar layout from inside the shell, so
the arrow runs `layout.py`, which rewrites `~/.config/omarchy/shell.json`
atomically (through symlinks, keeping the file's permissions). The bar reloads
on every toggle, so expect a short flicker. Hidden widgets keep their settings:
their full entries are stored on the arrow's own entry under `stash`.

## Uninstall

Put every hidden widget back first, then remove the plugin:

```bash
python3 ~/.config/omarchy/plugins/io.github.bryanperdana.bar-collapse/layout.py restore
omarchy plugin remove io.github.bryanperdana.bar-collapse
```

## Development

```bash
tests/run.sh
```

## License

MIT
