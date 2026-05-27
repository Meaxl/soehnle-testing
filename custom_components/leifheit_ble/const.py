"""Constants for the Leifheit BLE integration."""

from homeassistant.const import Platform

DOMAIN = "leifheit_ble"

CONF_ADDRESS = "address"
CONF_NAME = "name"

DEFAULT_NAME = "Leifheit BLE Device"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
]

# TODO: Replace these UUIDs with the real GATT service/characteristic UUIDs.
NOTIFY_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
NOTIFY_CHARACTERISTIC_UUID = "12345678-1234-5678-1234-56789abcdef1"
WRITE_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
WRITE_CHARACTERISTIC_UUID = "12345678-1234-5678-1234-56789abcdef2"

# TODO: Replace these example payloads with real protocol commands.
COMMAND_EXAMPLE = b"\xAA\x55"
COMMAND_SWITCH_ON = b"\x01"
COMMAND_SWITCH_OFF = b"\x00"
