__all__ = ["MksLabjack"]

import asyncio
from typing import Dict, Any, List

import numpy as np
from pymodbus.client import ModbusTcpClient  # type: ignore

from yaqd_core import HasLimits, HasPosition, HasTransformedPosition, IsDaemon

from ._bytes import *


class MKSLabjack(HasTransformedPosition, HasLimits, HasPosition, IsDaemon):
    _kind = "mks-labjack"

    clients: Dict[str, ModbusTcpClient] = {}

    def __init__(self, name, config, config_filepath):
        super().__init__(name, config, config_filepath)
        # grab client
        if self._config["address"] in MKSLabjack.clients:
            self._client = MKSLabjack.clients[self._config["address"]]
        else:
            self._client = ModbusTcpClient(config["address"])
            MKSLabjack.clients[self._config["address"]] = self._client

    def get_close(self) -> int:
        response = self._client.read_register(self._config["modbus_address_close"])
        return data_to_uint16(response.registers)

    def get_open(self) -> int:
        response = self._client.read_register(self._config["modbus_address_open"])
        return data_to_uint16(response.registers)

    def get_position(self):
        return self.to_transformed(self._state["position"])

    def _relative_to_transformed(self, relative_position):
        xp = [p["setpoint"] for p in self._config["calibration"]]
        fp = [p["measured"] for p in self._config["calibration"]]
        out = np.interp(relative_position, xp, fp)
        return out

    def set_close(self, value: int) -> None:
        data = uint16_to_data(value)
        self._client.write_register(self._config["modbus_address_close"], data)

    def set_open(self, value: int) -> None:
        data = uint16_to_data(value)
        self._client.write_register(self._config["modbus_address_open"], data)

    def _set_position(self, position):
        data = float32_to_data(position)
        self._client.write_registers(self._config["modbus_address_setpoint"], data)

    def _transformed_to_relative(self, transformed_position):
        xp = [p["measured"] for p in self._config["calibration"]]
        fp = [p["setpoint"] for p in self._config["calibration"]]
        return np.interp(transformed_position, xp, fp)

    async def update_state(self):
        while True:
            response = self._client.read_registers(self._config["modbus_address_readback"], 2)
            position = data_to_float32(response.registers)
            self._state["position"] = position
