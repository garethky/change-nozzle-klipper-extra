# Change Nozzles

Change the nozzle diameter on your klipper printer without editing the config and rebooting.

Adds one new command:
CHANGE_NOZZLE [EXTRUDER=<config_name>] [NOZZLE_DIAMETER=<nozzle_diameter>] [MAX_EXTRUDE_CROSS_SECTION=<pressure_advance_smooth_time>]

Exposes 2 new values on extruder objects:
```
extruder.nozzle_diameter
extruder.max_extruder_ratio
```

e.g.:
```
// printer['extruder'] = {'can_extrude': False,
// 'max_extrude_ratio': 7.899282073458969,
// 'nozzle_diameter': 0.4,
// 'power': 0.0,
// 'pressure_advance': 0.07,
// 'smooth_time': 0.04,
// 'target': 0.0,
// 'temperature': 21.99}
```

This can be used in purge line and calibration print macros that want to extrude
 an appropriate amount of plastic relative to the nozzle size.

## ⚠️ Warning: This extra is potentially brittle and may be broken by Klipper changes

This extra relies on some [internal details](https://github.com/Klipper3d/klipper/blame/4671cf2d0e3ec864e72766cb1f6e24f1a308f794/klippy/kinematics/extruder.py#L164) of Extruder.py not changing. The code is pretty stable and hasn't changed in around 4 years. But if you see this code change please file a bug here an dI will attempt to get it back up to date in a timely manner.

I'd prefer if this was a patch but this way its something the community can use while we work to merge this into klipper. The end of life plan here is to copy the pattern from how [frame expansion compensation](https://github.com/alchemyEngine/klipper_frame_expansion_comp/blob/a6e0fe0735604aef89cba6962e2cab08a8ac1895/frame_expansion_compensation.py#L69) was merged. You'll get an update that turns this into something that just prints a warning.

# Filaments - Filament Presets for Klipper

# Installing

Clone this git repo to your printers home directory (e.g. /home/pi):

```bash
git clone https://github.com/garethky/change-nozzle-klipper-extra.git
```

Then run the install script. The install script assumes that Klipper is also installed in your home directory under "klipper": `${HOME}/klipper`.

```bash
cd ~/change-nozzle-klipper-extra
./install.sh
```

Optionally you can tell Moonraker's update manager about this plugin by 
adding this configuration block to the `moonraker.conf` of your printer:

```text
[update_manager client Filaments]
type: git_repo
path: ~/change-nozzle-klipper-extra
primary_branch: mainline
origin: https://github.com/garethky/change-nozzle-klipper-extra.git
install_script: install.sh
managed_services: klipper
```

----

# G-Code Commands

### [change_nozzle]
The following commands are available when a [filaments config section](#filaments) is enabled.

#### CHANGE_NOZZLE
`CHANGE_NOZZLE EXTRUDER=<config_name>] [NOZZLE_DIAMETER=<nozzle_diameter>]
[MAX_EXTRUDE_CROSS_SECTION=<pressure_advance_smooth_time>]`: Set the 
`nozzle_diameter` and `max_extrude_cross_section` properties of an extruder 
(overriding the settings defined in an [extruder](Config_Reference.md#extruder 
config section). If EXTRUDER is not specified, it defaults to the extruder in
the the active hotend.

----

# Config Reference
This extra requires that you have `[save_variables]` set up. If you don't it will throw an exception on startup.

## [change-nozzle]
Enable the `CHANGE_NOZZLE` command
```
[change-nozzle]
```

----

# Usage Reference

## Nozzle Change Macros
You would generally set up some macros that set the nozzle diameter and give them friendly names:

```
[gcode_macro NOZZLE_40]
gcode:
    CHANGE_NOZZLE NOZZLE_DIAMETER=0.4

[gcode_macro NOZZLE_60]
gcode:
    CHANGE_NOZZLE NOZZLE_DIAMETER=0.6
```

You wouldn't normally need to specify the EXTRUDER because klipper always has an active extruder. In a multi-tool printer you switch active extruders first and then change the nozzle size.

## Selecting PRESSURE_ADVANCE from a single slicer filament

Slicers allow you run some custom gcodes for your filament and klipper users often use this to set the exact `PRESSURE_ADVANCE` for a filament. The `PRESSURE_ADVANCE` value for a specific filament varies with nozzle diameter. You could keep a different preset for every nozzle size but that is tedious. Now you can write a macro that takes in the pressure advance values for different nozzle sizes and sets the appropriate `ADVANCE` value based on what nozzle is in the printer when the print starts:

```
[gcode_macro _SET_PA_BY_NOZZLE]
gcode:
    {% set nozzle = params.NOZZLE}
    {% set nozzle_diameter = printer.toolhead.extruder.nozzle_diameter %}
    {% if nozzle == nozzle_diameter}
        SET_PRESSURE_ADVANCE ADVANCE={params.ADVANCE}
```

Then call the macro from the GCode in in your slicers filament preset:

```
_SET_PA_BY_NOZZLE NOZZLE=0.25 ADVANCE=1.2
_SET_PA_BY_NOZZLE NOZZLE=0.4 ADVANCE=0.8
_SET_PA_BY_NOZZLE NOZZLE=0.6 ADVANCE=0.3
```

`PRESSURE_ADVANCE` will only be set if the nozzle diameter on the active extruder matches the diameter of the NOZZLE parameter.

## Vary the Extruded Filament in Macros

If you are writing a macro that prints filament, such as a claibration macro, you can parameterize the macro such that the nozzle diameter and filament diameter are taken into account:

```
    {% set nozzle_diameter = printer.toolhead.extruder.nozzle_diameter %}
    {% set filament_diameter = printer.configfile.config["extruder"]["filament_diameter"]|float %}
    
```

In your macro code you can work out the amount of filament to extruder per unit distance if you know the layer height:

```
{% set layer_height = 0.2 %}
{% set line_width = nozzle_diameter %}
{% set extrusion_factor = line_width * layer_height / ((filament_diameter / 2)*(filament_diameter / 2) * 3.14159) | float %}
```

Then extrusion moves look like this:

```
    G1 X25 E{extrusion_factor * 25}
```

A simple purge line macro can be written that takes advantage of this to purge a nozzle appropriate amount of material when the print starts:
```
[gcode_macro PURGE_LINE]
gcode:
    SAVE_GCODE_STATE NAME=PURGE_LINE
    {% set purge_start_x = params.PRINT_START_X|default(5.0)|float %}
    {% set purge_start_y = params.PRINT_START_Y|default(-5.0)|float %}
    {% set layer_height = 0.3 %}
    {% set line_width = nozzle_diameter %}
    {% set filament_diameter = printer.configfile.config["extruder"]["filament_diameter"]|float %}
    {% set extrusion_factor = line_width * layer_height / ((filament_diameter / 2)*(filament_diameter / 2) * 3.14159) | float %}

    ; purge/prime nozzle
    G90 ; use absolute coordinates
    ; go to the start of the print area, but -5 in Y
    G1 X{purge_start_x} Y{purge_start_y} Z{layer_height} F7200.0 ; go to the purge start location
    G91 ; relative coordinates
    M83 ; extruder relative mode
    G92 E0.0
    G1 X40.0 E{extrusion_factor * 2 * 40} F1000.0  ; narrow start line
    G1 X40.0 E{extrusion_factor * 3 * 40} F1000.0  ; priming thick outro line
    G92 E0.0
    G1 X3.0 Y3.0 F1000.0    ; move the nozzle away from the end of the purge line so the print doesn't drag the nozzle back through it.
    G1 F7200.0

    RESTORE_GCODE_STATE NAME=PURGE_LINE
```