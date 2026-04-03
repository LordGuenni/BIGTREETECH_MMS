# Adapter of printer's Heaters
#
# Copyright (C) 2025-2026 Garvey Ding <garveyding@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from .base import BaseAdapter


class HeatersAdapter(BaseAdapter):
    def __init__(self):
        super().__init__()
        self._obj_name = "heaters"

    def _get_heaters(self):
        return self.safe_get(self._obj_name)

    def find_heater(self, heater_name):
        return self._get_heaters().lookup_heater(heater_name)

    def set_temperature(self, heater, temp, wait=True):
        self._get_heaters().set_temperature(heater, temp, wait)


# Global instance for singleton
heaters_adapter = HeatersAdapter()
