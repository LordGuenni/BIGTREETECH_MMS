# Support for MMS Endless Spool
# Well... I prefer to call it "Limit Spool"
#
# Copyright (C) 2026 Garvey Ding <garveyding@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from dataclasses import dataclass

from ..adapters import (
    extruder_adapter,
    gcode_adapter,
    printer_adapter
)
from ..core.exceptions import EndlessSpoolFailedError
from ..core.slot_pin import PinType


@dataclass(frozen=True)
class MMSEndlessSpoolConfig:
    log_flag: str = "==O=="
    truncate_distance: float = 2000
    truncate_orphan_distance: float = 200
    extrude_distance_max: float = 5000


class MMSEndlessSpool:
    def __init__(self):
        self.slot_sub = {
            0:1,
            1:2,
            2:3,
            3:0,
        }
        es_config = MMSEndlessSpoolConfig()
        self.log_flag = es_config.log_flag
        self.truncate_distance = es_config.truncate_distance
        self.truncate_orphan_distance = es_config.truncate_orphan_distance
        self.extrude_distance_max = es_config.extrude_distance_max

        self.pin_type = PinType()

        # Status
        self._enable = False
        self._activating = False

        self._inlet_slot_num = None

        # Klippy event handler
        printer_adapter.register_klippy_ready(
            self._handle_klippy_ready)

    def _handle_klippy_ready(self):
        self._initialize_mms()
        self._initialize_loggers()
        self._register()

    def _initialize_mms(self):
        self.mms = printer_adapter.get_mms()
        self.mms_brush = printer_adapter.get_mms_brush()
        self.mms_charge = printer_adapter.get_mms_charge()
        self.mms_delivery = printer_adapter.get_mms_delivery()
        self.mms_purge = printer_adapter.get_mms_purge()
        self.mms_swap = printer_adapter.get_mms_swap()

        self.mms_pause = self.mms.get_mms_pause()
        self.mms_resume = self.mms.get_mms_resume()
        self.mms_fil_detection = self.mms.get_mms_filament_detection()

        self._enable = self.mms.endless_spool_is_enabled() \
            and self.mms_purge.is_enabled()

    def _initialize_loggers(self):
        mms_logger = printer_adapter.get_mms_logger()
        self.log_info = mms_logger.create_log_info(console_output=True)
        self.log_warning = mms_logger.create_log_warning(console_output=True)

        self.log_info_s = mms_logger.create_log_info(console_output=False)
        self.log_warning_s = mms_logger.create_log_warning(
            console_output=False)
        self.log_error_s = mms_logger.create_log_error(console_output=False)

    # ---- Register ----
    def _register(self):
        if not self._enable:
            return

        for mms_slot in self.mms.get_mms_slots():
            slot_num = mms_slot.get_num()

            mms_slot.inlet.add_release_callback(
                callback=self._handle_inlet_is_released,
                params={"slot_num":slot_num}
            )
            if self.mms.get_entry():
                # Entry is set
                mms_slot.entry.add_release_callback(
                    callback=self._handle_entry_is_released,
                    params={"slot_num":slot_num}
                )
            else:
                mms_slot.gate.add_release_callback(
                    callback=self._handle_gate_is_released,
                    params={"slot_num":slot_num}
                )

        # Register callbacks
        print_observer = self.mms.get_print_observer()
        print_observer.register_pause_callback(self.deactivate)
        print_observer.register_finish_callback(self.deactivate)
        print_observer.register_resume_callback(self.activate)

    def _unregister(self):
        # if not self._enable:
        #     return

        for mms_slot in self.mms.get_mms_slots():
            slot_num = mms_slot.get_num()
            # Entry is set
            if self.mms.get_entry():
                mms_slot.entry.remove_release_callback(
                    callback=self._handle_entry_is_released,
                    params={"slot_num":slot_num}
                )
            else:
                mms_slot.gate.remove_release_callback(
                    callback=self._handle_gate_is_released,
                    params={"slot_num":slot_num}
                )

        print_observer = self.mms.get_print_observer()
        print_observer.unregister_pause_callback(self.deactivate)
        print_observer.unregister_finish_callback(self.deactivate)
        print_observer.unregister_resume_callback(self.activate)

    # ---- Status ----
    def is_enabled(self):
        return self._enable

    def is_activating(self):
        return self._activating

    def is_inlet_released(self, slot_num):
        return self._enable \
            and self._activating \
            and self._inlet_slot_num is not None \
            and slot_num == self._inlet_slot_num

    # ---- Handlers ----
    def _is_target(self, slot_num):
        # Not activating or not printing, skip
        if not self._enable \
            or not self._activating \
            or not self.mms.printer_is_printing():
            return False

        # Self is not charged slot, skip
        slot_num_c = self.mms_charge.get_charged_slot()
        if slot_num_c is None or slot_num != slot_num_c:
            return False

        return True

    def _pause_and_wait(self, slot_num):
        # MMS Buffer pause
        mms_buffer = self.mms.get_mms_slot(slot_num).get_mms_buffer()
        mms_buffer.deactivate_monitor()

        # Pause print
        if self.mms_pause.mms_pause():
            self.mms_resume.set_mms_swap_resume(
                func=self.mms_swap.cmd_SWAP,
                gcmd=gcode_adapter.easy_gcmd(
                    command=self.mms_swap.format_command(slot_num)
                )
            )
        else:
            self.log_warning_s(
                f"slot[{slot_num}] endless spool mms pause failed"
            )
            return False

        # Wait Toolhead idle
        if not self.mms_delivery.wait_toolhead():
            self.log_warning_s(
                f"slot[{slot_num}] wait toolhead idle timeout"
            )
            return False

        return True

    def _prepare_handle(self, slot_num, pin_type):
        if not self._is_target(slot_num):
            return False

        msg = f"slot[{slot_num}] endless spool '{pin_type}' released"
        self.log_info(f"{msg} {self.log_flag}")

        if not self._pause_and_wait(slot_num):
            raise EndlessSpoolFailedError(
                f"{msg} {self.log_flag}",
                self.mms.get_mms_slot(slot_num)
            )
            return False

        return True

    def _purge_long_distance(self, distance):
        speed = self.mms_purge.get_purge_speed()
        distance_once = self.mms_purge.get_purge_distance()
        distance_extruded = 0

        # Extrude until distance is satisfied
        while distance_extruded < distance:
            # Move to tray
            self.mms_purge.move_to_tray()
            # Extrude
            dist = min(distance_once, distance-distance_extruded)
            extruder_adapter.extrude(dist, speed)
            # Brush to clean nozzle
            if self.mms_brush.is_enabled():
                self.mms_brush.mms_brush()
            # Sum distance
            distance_extruded += dist

    def _find_slot_new(self, slot_num):
        slot_num_new = None
        slot_num_org = slot_num
        slot_num_checked = [slot_num]

        while not slot_num_new:
            slot_num_sub = self.slot_sub.get(slot_num, None)
            if slot_num_sub is None or slot_num_sub in slot_num_checked:
                break

            slot_num_checked.append(slot_num_sub)

            mms_slot_sub = self.mms.get_mms_slot(slot_num_sub)
            if mms_slot_sub.inlet.is_triggered():
                slot_num_new = slot_num_sub
            else:
                slot_num = slot_num_sub

        return slot_num_new

    def _update_mapping_and_resume(self, slot_num):
        slot_num_new = self._find_slot_new(slot_num)
        if slot_num_new is None:
            raise EndlessSpoolFailedError(
                f"slot[{slot_num}] have no mapping slot",
                self.mms.get_mms_slot(slot_num)
            )
            return
        self.mms_swap.update_mapping_slot_num(slot_num, slot_num_new)
        self.mms_resume.gcode_resume()

    def _handle_inlet_is_released(self, slot_num):
        p_type = self.pin_type.inlet
        if not self._is_target(slot_num):
            return

        msg = f"slot[{slot_num}] endless spool '{p_type}' released"
        self.log_info(f"{msg} {self.log_flag}")

        self._inlet_slot_num = slot_num

        # mms_slot = self.mms.get_mms_slot(slot_num)
        # mms_buffer = mms_slot.get_mms_buffer()
        # mms_buffer.deactivate_monitor()

        # # Make sure is not selecting
        # self.mms_delivery.deliver_async_task(
        #     self.mms_delivery.unselect,
        # )

    def _handle_gate_is_released(self, slot_num):
        p_type = self.pin_type.gate

        try:
            if not self._prepare_handle(slot_num, p_type):
                return

            # If Gate is released but
            # Inlet is still triggered, just resume
            mms_slot = self.mms.get_mms_slot(slot_num)
            if mms_slot.inlet.is_triggered():
                self.log_info(
                    f"slot[{slot_num}] "
                    f"'{self.pin_type.inlet}' is triggered, "
                    "resume immediately"
                )
                self.mms_resume.gcode_resume()
                return

            # Make sure is not selecting
            self.mms_delivery.mms_unselect()
            # Purge long distance to truncate bowden
            self.log_info(
                f"slot[{slot_num}] purge "
                f"{self.truncate_distance} mm begin"
            )
            self._purge_long_distance(self.truncate_distance)

            # Finally update slot mapping and resume
            self._update_mapping_and_resume(slot_num)

        except EndlessSpoolFailedError as e:
            self.log_error_s(e)
        except Exception as e:
            self.log_error_s(
                f"slot[{slot_num}] endless spool "
                f"'{p_type}' released error: {e}"
            )

    def _handle_entry_is_released(self, slot_num):
        p_type = self.pin_type.entry

        try:
            if not self._prepare_handle(slot_num, p_type):
                return

            # If Entry is released but
            # Inlet/Gate is still triggered, just resume
            mms_slot = self.mms.get_mms_slot(slot_num)
            if mms_slot.inlet.is_triggered():
                self.log_info(
                    f"slot[{slot_num}] "
                    f"'{self.pin_type.inlet}' is triggered, "
                    "resume immediately"
                )
                self.mms_resume.gcode_resume()
                return
            if mms_slot.gate.is_triggered():
                self.log_info(
                    f"slot[{slot_num}] "
                    f"'{self.pin_type.gate}' is triggered, "
                    "resume immediately"
                )
                self.mms_resume.gcode_resume()
                return

            # Finally update slot mapping and resume
            self._update_mapping_and_resume(slot_num)

        except EndlessSpoolFailedError as e:
            self.log_error_s(e)
        except Exception as e:
            self.log_error_s(
                f"slot[{slot_num}] endless spool "
                f"'{p_type}' released error: {e}"
            )

    # ---- Control ----
    def activate(self):
        if not self._enable:
            return
        self._activating = True
        self.log_info_s("MMS endless spool is activated")
        self.mms_fil_detection.disable()

    def deactivate(self):
        if not self._enable:
            return
        self._activating = False
        self.log_info_s("MMS endless spool is deactivated")
        self.mms_fil_detection.recover()
        self._inlet_slot_num = None

    def purge_truncate(self, slot_num):
        if not self._enable:
            return

        # Self is not charged slot, skip
        slot_num_c = self.mms_charge.get_charged_slot()
        if slot_num_c is None or slot_num != slot_num_c:
            return

        mms_slot = self.mms.get_mms_slot(slot_num)
        if mms_slot.inlet.is_triggered():
            return

        try:
            slot_num_new = self._find_slot_new(slot_num)
            if slot_num_new is None:
                raise EndlessSpoolFailedError(
                    f"slot[{slot_num}] have no mapping slot",
                    self.mms.get_mms_slot(slot_num)
                )
                return
            self.mms_swap.update_mapping_slot_num(slot_num, slot_num_new)
        except EndlessSpoolFailedError as e:
            self.log_warning(e)
            return

        if mms_slot.entry.is_set():
            self._purge_until_entry_release(slot_num)
            self._purge_long_distance(self.truncate_orphan_distance)
            return
        else:
            self._purge_long_distance(self.truncate_distance)

    def _purge_until_entry_release(self, slot_num):
        mms_slot = self.mms.get_mms_slot(slot_num)
        success = True

        # Check if entry sensor is set and triggered
        if mms_slot.entry_is_triggered():
            speed = self.mms_purge.get_purge_speed()
            distance = self.mms_purge.get_purge_distance()
            distance_extruded = 0

            # Make sure is not selecting
            self.mms_delivery.mms_unselect()
            # Extrude until entry is released
            while mms_slot.entry_is_triggered():
                # Move to tray
                self.mms_purge.move_to_tray()
                # Extrude
                extruder_adapter.extrude(distance, speed)
                # Brush to clean nozzle
                if self.mms_brush.is_enabled():
                    self.mms_brush.mms_brush()

                # Distance check
                distance_extruded += distance
                if distance_extruded >= self.extrude_distance_max:
                    self.log_warning_s(
                        f"slot[{slot_num}] total extrude distance "
                        f"reach limit {self.extrude_distance_max}mm, "
                        "break"
                    )
                    success = False
                    break

            return success
