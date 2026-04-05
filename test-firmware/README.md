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

```bash
source ~/esp/esp-idf/export.sh
cd /workspaces/Universal-ESP32-Workbench/test-firmware/build
python -m esptool --chip esp32 --port "rfc2217://workbench.local:4001?ign_set_control" --baud 460800 --before default-reset --after no-reset write-flash @flash_args
```

After flashing, reboot through the workbench API:

```bash
curl -sS -X POST http://workbench.local:8080/api/serial/reset \
  -H "Content-Type: application/json" \
  -d '{"slot":"SLOT1"}'
```

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
- Fix: hold **BOOT**, press **RESET/EN**, release **RESET/EN**, release **BOOT**, when the dots appear "..."
```

### Failed to connect / sync to ESP32 bootloader

- Cause: reset/boot timing issue, especially after previous failed flash attempts.
- Fix:
  1. Ensure slot is present and state is `idle`.
  2. Retry flash command.
  3. If still failing, run a reset and retry:

```bash
curl -sS -X POST http://workbench.local:8080/api/serial/reset \
  -H "Content-Type: application/json" \
  -d '{"slot":"SLOT1"}'
```

### "Device PID identification is only supported on COM and /dev/ serial ports"

- This line is informational when using RFC2217 URLs and can be ignored.
- It is not the root cause of flash failure.

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
