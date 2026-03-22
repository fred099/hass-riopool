# Riopool Rio750 - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/fred099/hass-riopool)](https://github.com/fred099/hass-riopool/releases)
[![License](https://img.shields.io/github/license/fred099/hass-riopool)](LICENSE)

Custom [Home Assistant](https://www.home-assistant.io/) integration for **Riopool / Starmatrix Rio750 Inverter WiFi BT** variable-speed pool pumps. Communicates entirely over your local network — no cloud dependency.

## Features

- **Local LAN control** via the Gizwits protocol (TCP port 12416)
- **Auto-discovery** of pumps on the network (UDP broadcast)
- **Variable speed control** — set speed from 1150 to 3450 RPM in 50 RPM steps
- **Real-time monitoring** — speed, power consumption, energy saving ratio
- **Fault detection** — binary sensors for all five hardware fault codes
- **Pump on/off** switch
- 5-second polling interval

## Supported Hardware

| Manufacturer | Model | Connectivity |
|---|---|---|
| Starmatrix / Riopool | Rio750 Inverter WiFi BT | WiFi (Gizwits MCU) |

Other Starmatrix/Riopool inverter pumps using the same Gizwits chipset may also work (e.g. Rio2600) but are untested.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right and select **Custom repositories**
3. Add `https://github.com/fred099/hass-riopool` with category **Integration**
4. Search for "Riopool" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/riopool` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **Riopool**
3. Enter the IP address of your pump (auto-discovery will suggest it if found)
4. The integration will verify the connection before completing setup

> **Tip:** Assign a static IP / DHCP reservation to your pump for reliable operation.

## Entities

### Sensors

| Entity | Description | Unit |
|---|---|---|
| `sensor.rio750_speed` | Current real-time pump speed | RPM |
| `sensor.rio750_power` | Current power consumption | W |
| `sensor.rio750_energy_saving` | Energy saving ratio | % |
| `sensor.rio750_mode` | Operating mode (Auto / Manual) | — |
| `sensor.rio750_manual_gear` | Manual gear preset (LOW / MEDI / HIGH / FULL) | — |

### Switches

| Entity | Description |
|---|---|
| `switch.rio750_pump` | Turn the pump on or off |

### Numbers

| Entity | Description | Range |
|---|---|---|
| `number.rio750_manual_speed` | Set manual speed | 1150–3450 RPM (step 50) |

### Binary Sensors (Fault Codes)

| Entity | Fault | Description |
|---|---|---|
| `binary_sensor.rio750_fault_tp` | TP | Motor temperature >90 °C or <-5 °C |
| `binary_sensor.rio750_fault_bp` | BP | Motor or impeller blocked |
| `binary_sensor.rio750_fault_ol` | OL | Overload / excessive current |
| `binary_sensor.rio750_fault_lp` | LP | Phase loss |
| `binary_sensor.rio750_fault_cp` | CP | Communication loss between display and main board |

## Important: LAN vs Cloud Limitations

The Rio750 uses a **Gizwits** WiFi module. This integration uses the **local LAN protocol** — it does not require internet access or a cloud account. However, the pump firmware only implements a subset of controls over LAN:

### What works over LAN (this integration)

- **Pump on/off** (`switch.rio750_pump`)
- **Manual speed** (`number.rio750_manual_speed`)
- **All status reading** — speed, power, mode, gear, timers, faults

### What does NOT work over LAN

The following settings are managed by the **Gizwits cloud** (via the Starmatrix app) and **cannot be changed** through this integration:

- Timer schedules (Time1–Time4 start/end/speed/enable)
- Operating mode (Auto/Manual)
- Manual gear presets (LOW/MEDI/HIGH/FULL)
- Auto switch

The Starmatrix app sends these settings through the cloud API, not directly to the pump. The entities for these values are exposed as **read-only sensors** so you can monitor them.

### Required: Manual Mode

The pump **must be set to Manual mode** via the Starmatrix app for speed control to work. If the pump is in Auto mode, it will ignore speed commands from this integration.

> **Warning:** Do not attempt to switch the pump to Auto mode via LAN — the pump will stop accepting LAN control commands and can only be recovered using the Starmatrix app.

## Technical Details

This integration communicates directly with the Gizwits WiFi module inside the pump over your local network. It does **not** use the Gizwits cloud API.

- **Protocol:** Gizwits LAN protocol (proprietary binary)
- **Transport:** TCP on port 12416
- **Discovery:** UDP broadcast on port 12414
- **Authentication:** Passcode exchange per TCP session
- **Polling:** Every 5 seconds
- **IoT class:** Local Polling

## Troubleshooting

- **Cannot connect:** Ensure the pump is powered on and connected to the same network/VLAN as Home Assistant. Check that TCP port 12416 is not blocked by firewall rules.
- **Intermittent disconnects:** Assign a static IP to the pump. The integration will automatically reconnect.
- **Speed not changing:** The pump must be in **Manual** mode for `number.rio750_manual_speed` to take effect.

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with, endorsed by, or associated with Starmatrix, Riopool, or Gizwits. Use at your own risk.
