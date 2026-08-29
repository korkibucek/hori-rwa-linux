# Per-game configurations

Ready-made configuration for specific games, so the wheel works well
out of the box instead of being treated as a thumbstick gamepad.

## Why games need this

The driver presents the wheel as an **Xbox 360 controller** (see the main
README). That gives instant compatibility everywhere, but it also means
games apply their *gamepad* input profile by default: steering deadzones,
input smoothing, and non-linear response curves designed for a 3 cm
thumbstick — not a 900° wheel. Racing games that let you configure input
per-device can almost always be fixed with a config file or a few menu
settings; the folders here capture exactly that, tested on real hardware.

## Layout

Each game gets one folder:

```
games/
  <game-name>/
    README.md      what the config does, where it goes, how it was verified
    <config files> drop-in files, paths documented in the folder README
  _template/       skeleton for adding a new game
```

Every folder README must state:

- **Status** — verified working (with date and setup) or untested
- **Install** — exact destination paths, for native Linux and Proton
- **What it changes and why** — per binding/setting, no magic
- **How it was derived** — so it can be redone after game updates

## Adding a game

Copy `_template/`, name the folder after the game (lowercase, dashes),
fill in the README, and test on real hardware before marking it verified.
General guidance that applies to most games:

- Steering should use the game's *direct*/*wheel* input mode with **zero
  deadzone** and **linear response** if the game exposes those knobs.
- Pedals: linear response; games often square trigger input by default.
- Gear shifting belongs on the two shifter paddles (LB/RB in the Xbox
  layout the driver presents).
- The wheel has no force feedback (yet) — disable FFB in-game if it
  causes warnings; centering is physical (spring).
