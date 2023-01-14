# Code for handling live nozzle swaps
#
# Copyright (C) 2023-2024  Gareth Farrington <gareth@waves.ky>
#
# This file may be distributed under the terms of the GNU GPLv3 license.


# This is written so it wont be too hard to port it into 
# https://github.com/Klipper3d/klipper/blob/master/klippy/kinematics/extruder.py
# So the objects are somewhat duplicated and the mehtodology is the same

import math, logging
import types

class ExtruderChangeNozzleExtension:
    def __init__(self, config, extruder_name, extensions):
        self.extruder_name = extruder_name
        self.nozzle_variable_key = '%s_nozzle' % (self.extruder_name)
        self.extensions = extensions
        self.config = config
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.extruder = self.printer.lookup_object(extruder_name)
        self.gcode = self.printer.lookup_object('gcode')
        self.save_variables = self.printer.lookup_object('save_variables', None)
        # this module requires save variables to work
        if self.save_variables is None:
            return
        # Register commands
        self.printer.register_event_handler("klippy:connect",
                                            self._handle_connect)
        if self.extruder_name == 'extruder':
            self.gcode.register_mux_command("CHANGE_NOZZLE", "EXTRUDER", None,
                        self.cmd_default_CHANGE_NOZZLE,
                        desc=self.cmd_default_CHANGE_NOZZLE_help)
        self.gcode.register_mux_command("CHANGE_NOZZLE", "EXTRUDER",
                    self.extruder_name, self.cmd_CHANGE_NOZZLE,
                    desc=self.cmd_default_CHANGE_NOZZLE_help)
    
    def change_nozzle(self, user_nozzle_diameter, user_max_cross_section):
        nozzle_diameter = self.config.getfloat('nozzle_diameter', above=0.)
        if not user_nozzle_diameter is None:
            nozzle_diameter = user_nozzle_diameter
        self.extruder.nozzle_diameter = nozzle_diameter
        # The extruder needs its internal variables updated for the new nozzle
        # copied from: https://github.com/Klipper3d/klipper/blob/master/klippy/kinematics/extruder.py#L164
        # Setup kinematic checks
        filament_diameter = self.config.getfloat(
            'filament_diameter', minval=nozzle_diameter)
        self.extruder.filament_area = math.pi * (filament_diameter * .5)**2
        def_max_cross_section = 4. * nozzle_diameter**2
        def_max_extrude_ratio = def_max_cross_section / self.extruder.filament_area
        max_cross_section = self.config.getfloat(
            'max_extrude_cross_section', def_max_cross_section, above=0.)
        if not user_max_cross_section is None:
            max_cross_section = user_max_cross_section
        self.extruder.max_extrude_ratio = max_cross_section / self.extruder.filament_area
        logging.info("Extruder max_extrude_ratio=%.6f", self.extruder.max_extrude_ratio)
        toolhead = self.printer.lookup_object('toolhead')
        max_velocity, max_accel = toolhead.get_max_velocity()
        self.extruder.max_e_velocity = self.config.getfloat(
            'max_extrude_only_velocity', max_velocity * def_max_extrude_ratio
            , above=0.)
        self.extruder.max_e_accel = self.config.getfloat(
            'max_extrude_only_accel', max_accel * def_max_extrude_ratio
            , above=0.)
    
    # Save extruder settings to [save_variables]
    def save(self, nozzle_diameter, max_cross_section):
        gcmd_save = self.gcode.create_gcode_command("SAVE_VARIABLE",
                        "SAVE_VARIABLE", {
                            'VARIABLE': self.nozzle_variable_key,
                            'VALUE': str({
                                'nozzle_diameter': nozzle_diameter,
                                'max_extrude_cross_section': max_cross_section
                            })
                        })
        self.save_variables.cmd_SAVE_VARIABLE(gcmd_save)
    
    def load(self):
        event_time = self.reactor.monotonic()
        vars = self.save_variables.get_status(event_time)['variables']
        if self.nozzle_variable_key in vars:
            return vars[self.nozzle_variable_key]
        return {'nozzle_diameter': None, 'max_extrude_cross_section': None}

    # wrap the status the object on the extruder so it includes nozzle_diameter
    def wrap_status(self):
        extruder = self.extruder
        wrapped_get_status = self.extruder.get_status
        #wrapped_get_status = self.extruder.get_status
        def get_status_wrapper(self, eventtime):
            sts = wrapped_get_status(eventtime)
            sts['nozzle_diameter'] = self.nozzle_diameter
            sts['max_extrude_ratio'] = self.max_extrude_ratio
            return sts
        extruder.get_status = types.MethodType(get_status_wrapper, extruder)

    def _handle_connect(self):
        # on startup, update nozzle settings to the ones in save_variables:
        nozzle_settings = self.load()
        self.wrap_status()
        self.change_nozzle(nozzle_settings['nozzle_diameter'],
                                nozzle_settings['max_extrude_cross_section'])

    cmd_default_CHANGE_NOZZLE_help = "Set nozzle diameter"
    def cmd_default_CHANGE_NOZZLE(self, gcmd):
        extruder = self.printer.lookup_object('toolhead').get_extruder()
        self.extensions[extruder.name].cmd_CHANGE_NOZZLE(gcmd)

    def cmd_CHANGE_NOZZLE(self, gcmd):
        diameter = gcmd.get_float('NOZZLE_DIAMETER', None, above=0.)
        max_cross_section = gcmd.get_float('MAX_EXTRUDE_CROSS_SECTION', None, above=0.)
        self.change_nozzle(diameter, max_cross_section)
        self.save(diameter, max_cross_section)

class ChangeNozzlePrinterObject:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.config = config
        self.extensions = {}
        # Register commands
        self.printer.register_event_handler("klippy:connect",
                                            self._handle_connect)

    # this has to run after all extruders get defined
    def _handle_connect(self):
        for i in range(99):
            section = 'extruder'
            if i:
                section = 'extruder%d' % (i,)
            if not self.config.has_section(section):
                break
            self.extensions[section] = ExtruderChangeNozzleExtension(
                    self.config.getsection(section), section, self.extensions)

    def get_status(self, eventtime):
        # this extension is not meant to provide state
        return {}

def load_config(config):
    return ChangeNozzlePrinterObject(config)