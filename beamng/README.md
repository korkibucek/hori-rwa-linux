# BeamNG.drive setup

BeamNG sees the driver's virtual pad as an Xbox controller ("xidevice") and
applies gamepad smoothing and a steering deadzone by default — bad for a
real wheel. This override switches the driving controls to the **Direct**
input filter (`filterType: 2`) with no deadzone and linear response, moves
gear shifting to the paddles (LB/RB), and puts the turn signals on the
L2/R2 clicks. Cross/A stays accept/action; the default A=shift-up and
X=shift-down gamepad bindings are removed.

Install: copy `028e045e.diff` into the game's user folder inputmaps
directory — on Linux under Proton that is

```
~/.local/share/BeamNG/BeamNG.drive/current/settings/inputmaps/
```

(also as `xidevice.diff` if the pid/vid variant isn't picked up), then
restart BeamNG. Verify under Options > Controls: steering should list
filter "Direct".
