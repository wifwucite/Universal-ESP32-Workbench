# Test Firmware Build and Flash Guide

This folder contains the ESP-IDF test firmware used to validate the Universal ESP32 Workbench features.

## Prerequisites

- ESP-IDF installed locally (examples below assume `~/esp/esp-idf`)
- Built firmware artifacts in this project
- Workbench reachable at `workbench.local`
- Device connected to `SLOT1` (`rfc2217://workbench.local:4001`)

## Build (ESP32)

Run from the repository root:

```bash
source ~/esp/esp-idf/export.sh
cd /workspaces/Universal-ESP32-Workbench/test-firmware
idf.py set-target esp32
idf.py build
```

Main outputs:

- `build/wb-test-firmware.bin`
- `build/bootloader/bootloader.bin`
- `build/partition_table/partition-table.bin`
- `build/ota_data_initial.bin`

## Flash via Workbench (SLOT1 / RFC2217 :4001)

Run from `test-firmware/`:

### Main option (based on DTR/RTS)

Note: If auto-reset is flaky on your board, adding a capacitor between EN and GND
(typically 1uF to 10uF, often 10uF) can improve timing reliability.

```bash
source ~/esp/esp-idf/export.sh
cd /workspaces/Universal-ESP32-Workbench/test-firmware/build
python -m esptool --chip esp32 --port "rfc2217://workbench.local:4001" --baud 460800 write-flash @flash_args
```

This relies on RFC2217 DTR/RTS control line toggling from esptool:

- DTR/RTS are modem control signals, not serial data bytes.
- On ESP32 auto-programming circuits, one line drives EN (reset) and the other
  influences GPIO0 (boot strap) through transistor logic.
- esptool's default pre-flash reset (`--before default_reset`) toggles these lines
  to reset the chip while GPIO0 is low at sampling time, entering ROM download mode.
- If timing works, flash starts without touching board buttons.

### Alternative options

#### When GPIOs are wired

```bash
# 1) Force download mode on SLOT1
curl -sS -X POST "http://workbench.local:8080/api/serial/recover" \
  -H "Content-Type: application/json" \
  -d '{"slot":"SLOT1"}'

# 2) Flash over RFC2217
python -m esptool --chip esp32 \
  --port "rfc2217://workbench.local:4001?ign_set_control" \
  --baud 460800 \
  --before no_reset --after no_reset \
  write-flash @flash_args

# 3) Release BOOT and reboot normally
curl -sS -X POST "http://workbench.local:8080/api/serial/release" \
  -H "Content-Type: application/json" \
  -d '{"slot":"SLOT1"}'
```

#### When GPIOs are not wired

Step 1: Press and hold the BOOT button, press and release the EN button (toggles the actual reboot/reset, with BOOT down it goes into flashing mode aka bootloader mode), after that release the BOOT button.

```bash
# 2) Flash over RFC2217
python -m esptool --chip esp32 \
  --port "rfc2217://workbench.local:4001?ign_set_control" \
  --connect-attempts 30
  --baud 460800 \
  --before no_reset --after no_reset \
  write-flash @flash_args
```
(Connect attempts allow for more time to press the buttons.)

Step 3: Press and release the EN button (without holding BOOT), reboots/resets the chip into normal execution mode.

## Optional: Verify Slot Mapping

```bash
curl -s http://workbench.local:8080/api/devices | jq .
```

Confirm `SLOT1` is present and mapped to RFC2217 port `4001` before flashing.

## Notes

- Keep `--after no_reset` when flashing over workbench RFC2217.
- Use `POST /api/serial/reset` after flash to boot firmware cleanly.
- Current defaults use 4MB flash layout (`partitions-4mb.csv`).

## Troubleshooting

### Flash command exits with code 2

This is a generic esptool failure. Re-run with the same command and inspect the first error line, then use the fixes below.

### Device is busy / failed to open port

- Cause: another client already connected to SLOT1 (serial monitor, IDE, previous script).
- Fix: close other serial clients and retry.
- Verify slot status:

```bash
curl -s http://workbench.local:8080/api/devices | jq .
```

### Could not resolve host or connect to workbench

- Cause: DNS/network issue or portal not reachable.
- Fix: confirm the host and API are reachable:

```bash
curl -s http://workbench.local:8080/api/info | jq .
```

### "Wrong boot mode detected (0x13)! The chip needs to be in download mode"

- Cause: the ESP32 booted normally instead of entering download mode. `--before default_reset` toggles DTR/RTS to trigger the auto-download circuit, but it is not working (no auto-download circuit on the board, or DTR/RTS not wired).
- Fix option 1 (manual): hold **BOOT**, press **RESET/EN**, release **RESET/EN**, release **BOOT**, when the dots appear "..."
- Fix option 2 (hardware): add a capacitor between EN and GND (typically 1uF to 10uF, often 10uF) to improve reset timing reliability, then retry the flash command.

### "Device PID identification is only supported on COM and /dev/ serial ports"

- This line is informational when using RFC2217 URLs and can be ignored.
- It is not the root cause of flash failure.

### RFC2217 control-line negotiation issues (`ign_set_control`)

- Symptom: esptool fails early, hangs during connect, or reports RFC2217 control
  negotiation issues while using a network serial URL.
- Fix: append `?ign_set_control` to the RFC2217 port URL.

Example:

```bash
python -m esptool --chip esp32 \
  --port "rfc2217://workbench.local:4001?ign_set_control" \
  --baud 460800 write-flash @flash_args
```

What this does:

- pyserial stops waiting for strict RFC2217 `SET_CONTROL` acknowledgments.
- DTR/RTS toggling still happens; only response handling is relaxed.

### Wrong chip / offset mismatch

- Cause: using non-ESP32 offsets for ESP32 or wrong chip argument.
- For classic ESP32, use:
  - `--chip esp32`
  - bootloader offset `0x1000`
  - partition table offset `0x8000`
  - ota data offset `0xf000`
  - app offset `0x20000`

### Flash size or partition errors

- Cause: flash size does not match selected partition table.
- Current project defaults are 4MB (`partitions-4mb.csv`).
- Keep `--flash_size 4MB` unless you intentionally rebuild with an 8MB layout.

### Device does not boot after successful flash

- Cause: expected on workbench when using `--after no_reset`.
- Fix: always issue reset after flash:

```bash
curl -sS -X POST http://workbench.local:8080/api/serial/reset \
  -H "Content-Type: application/json" \
  -d '{"slot":"SLOT1"}'
```
