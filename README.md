# mx5-miata-nd2-obd-can

## Telemetry Data for the ND2 MX-5 Miata

Documentation for things I've discovered on OBD2 and CAN buses on the ND2 MX-5 Miata. Can be used in applications like [RaceChrono](https://racechrono.com/) for racing telemetry.

There are two main data buses on the ND2 Miata: the OBD2 bus and the CAN bus. The OBD2 bus is used for diagnostics and is accessible through the OBD2 port, while the CAN bus is used for communication between various electronic control units (ECUs) in the vehicle. The CAN bus is also accessible through the ODB2 port.

In my testing it is possible to use an OBD splitter to connect to both the OBD2 and CAN buses at the same time! This allows for simultaneous access to both data streams, which can be useful for applications like RaceChrono that require real-time telemetry data. I used an [obdlink CX](https://www.obdlink.com/products/obdlink-cx/) and [obdlink MX+](https://www.obdlink.com/products/obdlink-mxp/) to connect to the CAN and ODB2 buses, respectively. Both of these adapters can run in either OBD2 or CAN mode. RaceChrono can be configured to read data from both buses simultaneously, allowing for a comprehensive view of the vehicle's performance.

I've included in this repository an export of my car configuration file from RaceChrono, which includes the data channels I have discovered on both the OBD2 and CAN buses. This configuration file can be imported into RaceChrono to quickly set up your own telemetry system for the ND2 Miata, and can be used as a reference for discovering additional data channels. The configuration file is located in the `RaceChrono` directory of this repository. Zip the `vehicleProfile.json` file and rename as `car.rcz` to import into RaceChrono.

Some data can be obtained from both the ODB2 and CAN buses, if so it is generally preferable to use the CAN bus as it is faster and more reliable. However, some data is only available on the OBD2 bus (tire pressures), so it may be necessary to use both buses if you want access to all available data.

All testing was performed on:

* 2020 US MX-5 Miata soft top 2.0 (ND2)
* 2021 US MX-5 Miata RF 2.0 (ND2)

## CAN Data Channels

| Channel | PID | Description | Units | RaceChrono Equation | notes |
| --- | --- | --- | --- | --- | --- |
| Accelerator Pedal Position | `514` | Accelerator Pedal Position | `%` | `E / 2.5` | |
| Ambient Air Temperature | `1056` | Ambient Air Temperature | `°C` | `((bytesToUInt(raw, 6, 2) - 65536) * 0.25 + 3200) / 100` | |
| Brake Pedal Position | `120` | Brake Pedal Position | `%` | `min(max(bitsToUInt(raw, 28, 12) - 156, 0) / 2.56, 100)` | |
| Clutch Pedal Position | `80` | Clutch Pedal Position | `%` | `(bytesToUInt(raw, 3, 1) - 1) * 100` | The car can only detect binary on/off for the clutch pedal, so returns 0% or 100% only. |
| Coolant Temperature | `1056` | Coolant Temperature | `°C` | `bytesToUInt(raw, 0, 1) - 40` | |
| Engine RPM | `514` | Engine RPM | `RPM` | `bytesToUInt(raw, 0, 2) / 4` | |
| Fuel Level | `1087` | Fuel Level | `%` | `((40895 - bytesToUInt(raw, 0, 2))) * 100 / 34944` | |
| Gear Selected | `357` | Gear Selected | `gear` | `7 - ((bytesToUInt(raw, 6, 2) > 800) + (bytesToUInt(raw, 6, 2) > 1100) + (bytesToUInt(raw, 6, 2) > 1400) + (bytesToUInt(raw, 6, 2) > 1800) + (bytesToUInt(raw, 6, 2) > 2500) + (bytesToUInt(raw, 6, 2) > 4000))` | Returns 1 for Neutral, 1-6 for gears 1-6, nothing for reverse. |
| Intake Air Temperature | `1056` | Intake Air Temperature | `°C` | `bytesToUInt(raw, 4, 1) - 40` | |
| Chassis Speed | `514` | Chassis Speed | `m/s` | `bytesToUInt(raw, 2, 2) / 360.0` |
| Steering Angle | `134` | Steering Angle | `°` | `(16000 - (bytesToUInt(raw, 0, 2))) * 0.1` | negative values are left, positive values are right. |
| Wheel Speed FL | `533` | Front Left Wheel Speed | `m/s` | `(bytesToUint(raw, 0, 2) - 10000) / 360.0` | |
| Wheel Speed FR | `533` | Front Right Wheel Speed | `m/s` | `(bytesToUint(raw, 2, 2) - 10000) / 360.0` | |
| Wheel Speed RL | `533` | Rear Left Wheel Speed | `m/s` | `(bytesToUint(raw, 4, 2) - 10000) / 360.0` | |
| Wheel Speed RR | `533` | Rear Right Wheel Speed | `m/s` | `(bytesToUint(raw, 6, 2) - 10000) / 360.0` | |

FL/FR/RL/RR confirmed by raising car and manually rotating indivdual wheels.

## OBD II Data Channels

Default Protocol: `ISO 15765-4 CAN (11 bit ID, 500 kbaud)`

| Channel | Header | PID | Description | Units | RaceChrono Equation | notes |
| --- | --- | --- | --- | --- | --- | --- |
| Tyre Pressure FL | `0x720` | `0x222A05` | Front Left Tyre Pressure | `kPa` | `(B * 1.373) + 20` | There are other formulas online for this, but I found this one to be closest to a hand held tire pressure gauge. You may need to adjust the offset and scale for your own tire pressure gauge, and calibrate each corner individually. The plus 20 here is example of a calibration offset. |
| Tyre Pressure FR | `0x720` | `0x222A07` | Front Right Tyre Pressure | `kPa` | `(B * 1.373) + 20` | Same as above. |
| Tyre Pressure RL | `0x720` | `0x222A06` | Rear Left Tyre Pressure | `kPa` | `(B * 1.373) + 20` | Same as above. |
| Tyre Pressure RR | `0x720` | `0x222A08` | Rear Right Tyre Pressure | `kPa` | `(B * 1.373) + 20` | Same as above. |

FL/FR/RL/RR confirmed by manually deflating each corner. The miata automatically works which wireless TPMS sensor is in which corner as you drive, via a clever process I can't be bothered to document here today...

## Example Dual Bus Connection in Car

Here is an example of using an ODB2 splitter to connect to both the OBD2 and CAN buses at the same time. The OBD2 splitter is connected to the OBD2 port in the car, and then two adapters are connected to the splitter: one for the OBD2 bus and one for the CAN bus. This allows for simultaneous access to both data streams.

To best of my knowledge, there is not currently an adapter that can read both OBD and CAN data simultaneously into RaceChrono, so splitter appears best option for now.

Example video output with telemetry: [https://www.youtube.com/watch?v=UJFE5DQPh1A](https://www.youtube.com/watch?v=UJFE5DQPh1A)

![alt text](/img/splitter.jpg "OBD2 Splitter")
![alt text](/img/dual-readers.jpg "Dual Readers")
