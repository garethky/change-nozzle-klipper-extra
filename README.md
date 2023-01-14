# Change Nozzles

Change the nozzle size on your klipper printer without editing the config and rebooting.

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
