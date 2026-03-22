"""Gizwits LAN protocol implementation for local communication with the pool pump.

Protocol details:
- TCP port 12416, UDP discovery on port 12414
- Status wBitBuf (bytes 0-1) is byte-swapped on the wire vs native MCU order
- Control commands need wBitBuf in native (un-swapped) order
- attrFlags (4 bytes) are byte-reversed (gizByteOrderExchange)
- Sequence numbers must increment per session to avoid deduplication
"""

import asyncio
import struct
from typing import Optional

from .const import (
    GIZWITS_HEADER,
    LAN_PORT,
    DISCOVERY_PORT,
    LOGGER,
    SPEED_RATIO,
)


class GizwitsLanClient:
    """Client for communicating with a Gizwits device over LAN."""

    # Mapping of attribute names to their flag bit position in attrFlags_t.
    # Ordered by Gizwits API datapoint id (0-24).
    ATTR_FLAG_BITS = {
        "ManualSwitch": 0,
        "Time1_enable": 1,
        "Time2_enable": 2,
        "Time3_enable": 3,
        "Time4_enable": 4,
        "AutoSwitch": 5,
        "Mode": 6,
        "ManualGear": 7,
        "Time1_speed": 8,
        "Time2_speed": 9,
        "Time3_speed": 10,
        "Time4_speed": 11,
        "Hour": 12,
        "Minute": 13,
        "Second": 14,
        "Reset": 15,
        "ManualSetSpeed": 16,
        "Time1_start": 17,
        "Time1_end": 18,
        "Time2_start": 19,
        "Time2_end": 20,
        "Time3_start": 21,
        "Time3_end": 22,
        "Time4_start": 23,
        "Time4_end": 24,
    }

    def __init__(self, host: str):
        self._host = host
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._seq_counter = 0
        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        return self._host

    def _next_seq(self) -> bytes:
        """Get next sequence number (4 bytes, big-endian)."""
        self._seq_counter += 1
        return struct.pack(">I", self._seq_counter)

    async def connect(self) -> bool:
        """Connect to the device and authenticate."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, LAN_PORT), timeout=5
            )
            self._seq_counter = 0

            # Request passcode (cmd 0x06)
            await self._send_command(b"\x00\x06")
            response = await self._read_response()
            if not response or len(response) < 10:
                LOGGER.error("Invalid passcode response from %s", self._host)
                await self.disconnect()
                return False

            passcode = response[8:]

            # Login with passcode (cmd 0x08)
            await self._send_command(b"\x00\x08", passcode)
            login_resp = await self._read_response()
            if not login_resp or login_resp[-1] != 0x00:
                LOGGER.error("Login failed for device %s", self._host)
                await self.disconnect()
                return False

            LOGGER.debug("Successfully connected and authenticated with %s", self._host)
            return True

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            LOGGER.error("Failed to connect to %s: %s", self._host, e)
            await self.disconnect()
            return False

    async def disconnect(self):
        """Close the connection."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def read_status(self) -> Optional[dict]:
        """Read device status and return parsed data points."""
        async with self._lock:
            try:
                if not self._writer:
                    if not await self.connect():
                        return None

                payload = await self._read_raw_status()
                if payload is not None:
                    return self._parse_status(payload)

                LOGGER.error("Failed to get status response from %s", self._host)
                await self.disconnect()
                return None

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                LOGGER.error("Error reading status from %s: %s", self._host, e)
                await self.disconnect()
                return None

    async def send_control(self, attrs: dict) -> bool:
        """Send control command to the device.

        Reads current status first, merges the requested changes into the
        writable portion (bytes 0-26), and sends with proper attrFlags.

        The wBitBuf (bytes 0-1) is byte-swapped in status reports. For control
        commands, we un-swap it back to native MCU byte order.

        attrs: dict of attribute names to values, e.g.:
            {"ManualSwitch": True}
            {"ManualSetSpeed": 28}  (raw value, not RPM)
        """
        async with self._lock:
            try:
                if not self._writer:
                    if not await self.connect():
                        return False

                # Read current status to use as base for the control payload
                current_raw = await self._read_raw_status()
                if current_raw is None or len(current_raw) < 27:
                    LOGGER.error("Cannot send control: failed to read current status")
                    return False

                # Build attrFlags (4 bytes) indicating which datapoints changed
                attr_flags = self._build_attr_flags(attrs)

                # Build modified attrVals (27 bytes) from current state
                attr_vals = self._build_control_payload(attrs, current_raw)
                if attr_vals is None:
                    return False

                # Send control command (cmd 0x93)
                # Format: [seq 4B] [p0 action=0x01] [attrFlags 4B] [attrVals 27B]
                seq = self._next_seq()
                await self._send_command(
                    b"\x00\x93", seq + b"\x01" + attr_flags + attr_vals
                )

                # Read acknowledgement
                response = await self._read_response()
                LOGGER.debug("Control response: %s", response.hex() if response else "None")
                return True

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                LOGGER.error("Error sending control to %s: %s", self._host, e)
                await self.disconnect()
                return False

    async def _read_raw_status(self) -> Optional[bytes]:
        """Read raw status payload (34 bytes) from device."""
        seq = self._next_seq()
        await self._send_command(b"\x00\x93", seq + b"\x02")
        all_data = b""
        for _ in range(5):
            chunk = await self._read_response(timeout=2.0)
            if chunk is None:
                break
            all_data += chunk
            payload = self._extract_status_payload(all_data)
            if payload is not None:
                return payload
        return None

    async def send_heartbeat(self) -> bool:
        """Send heartbeat to keep connection alive."""
        try:
            if not self._writer:
                return False
            await self._send_command(b"\x00\x15")
            response = await self._read_response()
            return response is not None
        except Exception:
            await self.disconnect()
            return False

    async def _send_command(self, command: bytes, payload: bytes = b""):
        """Send a Gizwits LAN protocol command."""
        flag = b"\x00"
        data = flag + command + payload
        length = len(data).to_bytes(1, byteorder="big")
        packet = GIZWITS_HEADER + length + data
        LOGGER.debug("Sending: %s", packet.hex())
        self._writer.write(packet)
        await self._writer.drain()

    async def _read_response(self, timeout: float = 3.0) -> Optional[bytes]:
        """Read response from the device."""
        try:
            data = await asyncio.wait_for(
                self._reader.read(4096), timeout=timeout
            )
            if data:
                LOGGER.debug("Received: %s", data.hex())
            return data if data else None
        except asyncio.TimeoutError:
            LOGGER.debug("Read timeout from %s", self._host)
            return None

    def _extract_status_payload(self, response: bytes) -> Optional[bytes]:
        """Extract the status data payload from a response.

        Handles both cmd 0x91 (unsolicited status) and cmd 0x94 (response to 0x93).
        For cmd 0x94: payload has 4 seq bytes before p0 action byte.
        For cmd 0x91: payload has p0 action byte immediately after cmd.
        """
        idx = 0
        while idx < len(response) - 8:
            if response[idx:idx + 4] == GIZWITS_HEADER:
                length_start = idx + 4
                msg_len, leb_size = self._decode_leb128(response[length_start:])
                if msg_len is None:
                    idx += 1
                    continue

                msg_start = length_start + leb_size
                msg_end = msg_start + msg_len

                if msg_end > len(response):
                    break

                if msg_start + 3 <= len(response):
                    cmd = response[msg_start + 1:msg_start + 3]

                    if cmd == b"\x00\x91":
                        p0_start = msg_start + 3
                        p0_action = response[p0_start] if p0_start < msg_end else None
                        if p0_action in (0x03, 0x04):
                            return response[p0_start + 1:msg_end]

                    elif cmd == b"\x00\x94":
                        p0_start = msg_start + 3 + 4  # skip 4 seq bytes
                        p0_action = response[p0_start] if p0_start < msg_end else None
                        if p0_action in (0x03, 0x04):
                            return response[p0_start + 1:msg_end]

                idx = msg_end
            else:
                idx += 1

        return None

    def _decode_leb128(self, data: bytes):
        """Decode LEB128/VLQ encoded length."""
        result = 0
        shift = 0
        for i, byte in enumerate(data):
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                return result, i + 1
            shift += 7
        return None, 0

    def _parse_status(self, payload: bytes) -> dict:
        """Parse status payload into named data points.

        The wBitBuf (bytes 0-1) is byte-swapped on the wire by the firmware's
        gizByteOrderExchange. We un-swap to get the native bit layout where:
          native byte 0: ManualSwitch(b0), Time1-4_enable(b1-4),
                         AutoSwitch(b5), Mode(b6), ManualGear_bit0(b7)
          native byte 1: ManualGear_bit1(b0)
        """
        if len(payload) < 34:
            LOGGER.error("Status payload too short: %d bytes (need 34)", len(payload))
            return {}

        data = {}

        # Un-swap wBitBuf: wire byte 1 = native byte 0, wire byte 0 = native byte 1
        native_b0 = payload[1]
        native_b1 = payload[0]
        flags_word = native_b0 | (native_b1 << 8)

        data["ManualSwitch"] = bool(flags_word & (1 << 0))
        data["Time1_enable"] = bool(flags_word & (1 << 1))
        data["Time2_enable"] = bool(flags_word & (1 << 2))
        data["Time3_enable"] = bool(flags_word & (1 << 3))
        data["Time4_enable"] = bool(flags_word & (1 << 4))
        data["AutoSwitch"] = bool(flags_word & (1 << 5))

        mode_idx = (flags_word >> 6) & 0x01
        data["Mode"] = ["Auto", "Manual"][mode_idx]

        gear_idx = (flags_word >> 7) & 0x03
        gears = ["LOW", "MEDI", "HIGH", "FULL"]
        data["ManualGear"] = gears[gear_idx] if gear_idx < 4 else "LOW"

        # Speed values (uint8, raw - multiply by SPEED_RATIO for RPM)
        data["Time1_speed"] = payload[2]
        data["Time2_speed"] = payload[3]
        data["Time3_speed"] = payload[4]
        data["Time4_speed"] = payload[5]

        # Clock
        data["Hour"] = payload[6]
        data["Minute"] = payload[7]
        data["Second"] = payload[8]

        # Reset command
        data["Reset"] = payload[9]

        # Manual speed (raw)
        data["ManualSetSpeed"] = payload[10]

        # Timer start/end times (uint16, big-endian, minutes from midnight)
        data["Time1_start"] = struct.unpack(">H", payload[11:13])[0]
        data["Time1_end"] = struct.unpack(">H", payload[13:15])[0]
        data["Time2_start"] = struct.unpack(">H", payload[15:17])[0]
        data["Time2_end"] = struct.unpack(">H", payload[17:19])[0]
        data["Time3_start"] = struct.unpack(">H", payload[19:21])[0]
        data["Time3_end"] = struct.unpack(">H", payload[21:23])[0]
        data["Time4_start"] = struct.unpack(">H", payload[23:25])[0]
        data["Time4_end"] = struct.unpack(">H", payload[25:27])[0]

        # Read-only values
        data["EnergySavingRatio"] = payload[27]
        data["Model"] = payload[28]
        data["RealtimeSpeed"] = struct.unpack(">H", payload[29:31])[0]
        data["Power"] = struct.unpack(">H", payload[31:33])[0]

        # Fault flags (byte 33)
        fault_byte = payload[33]
        data["TP"] = bool(fault_byte & (1 << 0))
        data["BP"] = bool(fault_byte & (1 << 1))
        data["OL"] = bool(fault_byte & (1 << 2))
        data["LP"] = bool(fault_byte & (1 << 3))
        data["CP"] = bool(fault_byte & (1 << 4))

        return data

    def _build_attr_flags(self, attrs: dict) -> bytes:
        """Build 4-byte attrFlags indicating which datapoints are being set.

        Each writable datapoint has a bit position (0-24). The 4-byte flag
        field is byte-reversed (gizByteOrderExchange) for the wire format.
        """
        flags = bytearray(4)
        for name in attrs:
            bit = self.ATTR_FLAG_BITS.get(name)
            if bit is not None:
                byte_idx = bit // 8
                bit_idx = bit % 8
                flags[byte_idx] |= 1 << bit_idx

        # Byte-reverse for wire format
        return bytes(reversed(flags))

    def _build_control_payload(self, attrs: dict, current_raw: bytes) -> Optional[bytes]:
        """Build attrVals by merging changes into the current state.

        Takes the current raw status (34 bytes) and copies the writable portion
        (bytes 0-26). The wBitBuf (bytes 0-1) is un-swapped from wire order to
        native MCU byte order before modification and sending.
        """
        payload = bytearray(current_raw[:27])

        # Un-swap wBitBuf from wire order to native MCU order
        payload[0], payload[1] = payload[1], payload[0]

        # Read current flags word in native byte order
        flags_word = payload[0] | (payload[1] << 8)

        for name, value in attrs.items():
            if name == "ManualSwitch":
                if value:
                    flags_word |= (1 << 0)
                else:
                    flags_word &= ~(1 << 0)
            elif name == "Time1_enable":
                if value:
                    flags_word |= (1 << 1)
                else:
                    flags_word &= ~(1 << 1)
            elif name == "Time2_enable":
                if value:
                    flags_word |= (1 << 2)
                else:
                    flags_word &= ~(1 << 2)
            elif name == "Time3_enable":
                if value:
                    flags_word |= (1 << 3)
                else:
                    flags_word &= ~(1 << 3)
            elif name == "Time4_enable":
                if value:
                    flags_word |= (1 << 4)
                else:
                    flags_word &= ~(1 << 4)
            elif name == "AutoSwitch":
                if value:
                    flags_word |= (1 << 5)
                else:
                    flags_word &= ~(1 << 5)
            elif name == "Mode":
                mode_idx = ["Auto", "Manual"].index(value) if value in ["Auto", "Manual"] else 0
                flags_word = (flags_word & ~(1 << 6)) | (mode_idx << 6)
            elif name == "ManualGear":
                gears = ["LOW", "MEDI", "HIGH", "FULL"]
                gear_idx = gears.index(value) if value in gears else 0
                flags_word = (flags_word & ~(0x03 << 7)) | (gear_idx << 7)
            elif name == "Time1_speed":
                payload[2] = int(value)
            elif name == "Time2_speed":
                payload[3] = int(value)
            elif name == "Time3_speed":
                payload[4] = int(value)
            elif name == "Time4_speed":
                payload[5] = int(value)
            elif name == "ManualSetSpeed":
                payload[10] = int(value)
            elif name == "Time1_start":
                struct.pack_into(">H", payload, 11, int(value))
            elif name == "Time1_end":
                struct.pack_into(">H", payload, 13, int(value))
            elif name == "Time2_start":
                struct.pack_into(">H", payload, 15, int(value))
            elif name == "Time2_end":
                struct.pack_into(">H", payload, 17, int(value))
            elif name == "Time3_start":
                struct.pack_into(">H", payload, 19, int(value))
            elif name == "Time3_end":
                struct.pack_into(">H", payload, 21, int(value))
            elif name == "Time4_start":
                struct.pack_into(">H", payload, 23, int(value))
            elif name == "Time4_end":
                struct.pack_into(">H", payload, 25, int(value))

        # Write back flags word in native byte order
        payload[0] = flags_word & 0xFF
        payload[1] = (flags_word >> 8) & 0xFF

        return bytes(payload)


async def discover_devices(timeout: float = 5.0) -> list[dict]:
    """Discover Gizwits devices on the local network via UDP broadcast."""
    devices = []

    class DiscoveryProtocol(asyncio.DatagramProtocol):
        def __init__(self):
            self.transport = None

        def connection_made(self, transport):
            self.transport = transport
            msg = GIZWITS_HEADER + b"\x03\x00\x00\x03"
            transport.sendto(msg, ("255.255.255.255", DISCOVERY_PORT))

        def datagram_received(self, data, addr):
            try:
                if len(data) > 32:
                    did_len = data[9]
                    did = data[10:10 + did_len].decode("ascii", errors="replace")
                    devices.append({"host": addr[0], "device_id": did})
                    LOGGER.debug("Discovered device at %s: %s", addr[0], did)
            except Exception as e:
                LOGGER.debug("Error parsing discovery response: %s", e)

    loop = asyncio.get_event_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        DiscoveryProtocol,
        local_addr=("0.0.0.0", 0),
        allow_broadcast=True,
    )

    try:
        await asyncio.sleep(timeout)
    finally:
        transport.close()

    return devices
