# BeamNG.drive

**Status:** verified working 2026-08-29 — BeamNG.drive under Proton on
Bazzite (Steam appid 284160), wheel driver v3 with the confirmed button
layout.

## What this does

BeamNG detects the driver's virtual pad as an Xbox controller (device
type `xidevice`) and applies its gamepad profile: ~10% steering deadzone,
input smoothing, `linearity 2.5` on steering and `linearity 2` on the
triggers (input is raised to that power), and gear shifting on the A/X
face buttons. With a real wheel that feels vague and laggy.

The override in `028e045e.diff` switches the driving controls to BeamNG's
**Direct** input filter and makes them linear:

| Control (wheel)     | xidevice control | Action                | Change vs stock |
|---------------------|------------------|-----------------------|-----------------|
| Steering            | `thumblx`        | `steering`            | filter Direct (`filterType: 2`), deadzone 0, linearity 1 — raw 1:1 |
| Right pedal         | `triggerr`       | `accelerate`          | filter Direct, linearity 1 (stock squares the input) |
| Left pedal          | `triggerl`       | `brake`               | filter Direct, linearity 1 |
| Right shifter paddle| `btn_r`          | `shiftUp`             | new binding |
| Left shifter paddle | `btn_l`          | `shiftDown`           | new binding |
| L2 click            | `btn_lt`         | `toggle_left_signal`  | new binding (stick-click in the Xbox layout, otherwise wasted) |
| R2 click            | `btn_rt`         | `toggle_right_signal` | new binding |
| Cross (A)           | `btn_a`          | accept / action       | stock, but the stock `A = shiftUp` binding is **removed** |
| Square (X)          | `btn_x`          | (stock menu duties)   | stock `X = shiftDown` binding is **removed** |

Everything not listed (menus, cameras on the d-pad, pause, photo mode…)
keeps BeamNG's stock xidevice bindings.

## Install

Copy `028e045e.diff` into BeamNG's **userfolder** inputmaps directory and
restart the game:

- Proton (as on Bazzite): `~/.local/share/BeamNG/BeamNG.drive/current/settings/inputmaps/`
- Native Linux build: same path (the userfolder is shared)
- Windows: `%LocalAppData%\BeamNG.drive\<version>\settings\inputmaps\`

Create the `inputmaps` directory if it doesn't exist. If the game doesn't
pick the file up (different pid/vid seen through another translation
layer), also copy it as `xidevice.diff` in the same directory — that name
matches *any* Xbox-mode controller.

## Verify

Options → Controls → search "steering": the wheel's steering binding
should show input filter **Direct**. On the pause screen the vehicle
should respond 1:1 to small wheel movements with no lag and no dead
region around center.

## How it was derived

- BeamNG loads per-device inputmaps by file name: `<pid><vid>` lowercase
  (product ID first — the DualShock 4 stock file is `05c4054c.json`), or
  a device-type name like `xidevice`. Stock maps live in the install dir
  under `settings/inputmaps/`; user overrides go in the userfolder as
  `.diff` files with the same JSON shape plus an optional `"removed"`
  list (see `lua/ge/extensions/core/input/bindings.lua`,
  `getInputmapPaths`/`getWritingPath`).
- The driver's virtual pad is `045e:028e`, so the file is `028e045e.diff`.
- Control names come from the stock `settings/inputmaps/xidevice.json`:
  `thumblx/y`, `thumbrx/y`, `triggerl/r`, `btn_a/b/x/y`, `btn_l/r`
  (shoulders), `btn_lt/rt` (stick clicks), `btn_back/start`,
  `upov/dpov/lpov/rpov`, with `modifier1`/`modifier2` prefixes.
- Filter constants are in `lua/common/inputFilters.lua`:
  `FILTER_KBD = 0`, `FILTER_PAD = 1`, `FILTER_DIRECT = 2`.
- After a game update, re-check the stock `xidevice.json` for renamed
  actions; the `.diff` only overrides what it names.
