# Project journal

Ordered in descending chronological order.

## 26-04-12 (Session 1 - Multi-target debug-test builds)

### Summary

Built the debug-test firmware for three ESP32 variants (S3, C6, standard ESP32) using target-specific commands. Confirmed each build succeeds and generates proper binaries for its platform.

### What we did

- Built debug-test for **ESP32-S3** (pre-existing C6 target was already set):
  ```bash
  cd /workspaces/Universal-ESP32-Workbench/debug-test
  source /opt/esp-idf/export.sh
  idf.py set-target esp32s3
  idf.py build
  ```
  - Binary generated: `build/debug-test.bin` (~231 KB), 78% free in app partition.

- Built debug-test for **ESP32-C6**:
  ```bash
  cd /workspaces/Universal-ESP32-Workbench/debug-test
  source /opt/esp-idf/export.sh
  idf.py set-target esp32c6
  idf.py build
  ```
  - Binary generated: `build/debug-test.bin` (~177 KB), 83% free in app partition.
  - Verified: `CONFIG_IDF_TARGET="esp32c6"` in `sdkconfig`.

- Built debug-test for **standard ESP32**:
  ```bash
  cd /workspaces/Universal-ESP32-Workbench/debug-test
  source /opt/esp-idf/export.sh
  idf.py set-target esp32
  idf.py build
  ```
  - Binary generated: `build/debug-test.bin` (182 KB).
  - Verified: `CONFIG_IDF_TARGET="esp32"` in `sdkconfig`.

### Learnings

- **Target switching** with `idf.py set-target <target>` cleanly updates `sdkconfig` and regenerates the CMake build tree; no manual sdkconfig editing needed.
- **ESP-IDF environment** must be sourced *before* running any `idf.py` commands (e.g., `source /opt/esp-idf/export.sh`), even across multiple builds in the same shell session.

## 26-04-11 (Session 2 - ESP32-C3 RGB LED compilation)

### Summary

Extended debug-test firmware to support ESP32-C3 with onboard RGB LED at GPIO8, and successfully compiled the project for C3 target.

### What we did

- Added ESP32-C3 target-specific branch to `debug-test/main/main.c`:
  - Added `#elif defined(CONFIG_IDF_TARGET_ESP32C3)` condition with `#define RGB_GPIO 8`.
  - Updated LED strip include guard to compile for both ESP32-S3 and ESP32-C3: `#if defined(CONFIG_IDF_TARGET_ESP32S3) || defined(CONFIG_IDF_TARGET_ESP32C3)`.
  - Firmware now cycles RGB LED red → green → blue → off every 500 ms on C3 boards (same as S3 behavior).
- Compiled the debug-test project for ESP32-C3 using `idf.py set-target esp32c3` and `idf.py build`.
- Resolved missing ESP-IDF toolchain component (`riscv32-esp-elf-gdb`) by running the tool installer.

## 26-04-11 (Session 1 - NetworkManager diagnostics)

### Summary

Investigated how to diagnose missing WiFi profiles on Raspberry Pi Zero W when adding NetworkManager connection files manually.

### What we did

- Reviewed a practical troubleshooting flow for new files under `/etc/NetworkManager/system-connections/`:
  - verify ownership and permissions (`root:root`, typically `chmod 600`),
  - reload profiles (`nmcli connection reload`),
  - list loaded profiles (`nmcli connection show`),
  - inspect NetworkManager logs with `journalctl -u NetworkManager`.
- Captured multiple methods to scan visible SSIDs:
  - `nmcli device wifi rescan` + `nmcli device wifi list`,
  - `iw dev wlan0 scan | grep SSID`,
  - `iwlist wlan0 scan` (legacy fallback),
  - `wpa_cli scan` / `wpa_cli scan_results` when `wpa_supplicant` is active.
- Added a quick operational reference for `nmtui` as an interactive way to create/edit/activate WiFi profiles without hand-editing `.nmconnection` files.

### Learnings

- NetworkManager may ignore a manually added profile if file mode/owner is wrong, even if the content looks valid.
- `nmcli` is the most reliable first-line tool for both scanning SSIDs and validating whether a profile was actually loaded.
- `nmtui` is a useful low-friction recovery path on headless/SSH sessions when profile syntax is uncertain.
- If scans return no networks, check interface state first (`nmcli device status`, `ip link show wlan0`) before debugging credentials.

## 26-04-06

### Summary

First day working with the ESP32-S3 debug-test firmware and the Universal ESP32 Workbench toolchain.

### Changes made

**debug-test firmware (`debug-test/main/`)**
- Added RGB LED support for ESP32-S3 using the `led_strip` RMT driver.
  - Added an `#if defined(CONFIG_IDF_TARGET_ESP32S3)` / `#endif` guard around all RGB code so non-S3 targets continue using the existing GPIO blink path.
  - RGB data pin is GPIO48 (common on many S3 dev boards; check board schematic if LED is unresponsive).
  - `debug_loop()` now cycles Red → Green → Blue → Off every 500 ms on S3.
  - `app_main()` calls `rgb_init()` instead of `gpio_set_direction()` on S3.
- Updated `CMakeLists.txt` to declare `REQUIRES led_strip esp_driver_gpio` — required by ESP-IDF 5.4 which splits drivers into separate components.
- Created `main/idf_component.yml` to pull `espressif/led_strip ^2.5.2` via the IDF Component Manager (downloaded as `managed_components/espressif__led_strip`).

**Repository hygiene**
- Added `**/managed_components/` to `.gitignore` — the downloaded component cache should not be committed; `idf_component.yml` and `dependencies.lock` are sufficient.

### Learnings

**ESP-IDF 5.x vs 4.x differences**
- `led_strip` is no longer a built-in IDF component; it must be declared in `idf_component.yml` and fetched via the Component Manager (or vendored explicitly).
- GPIO and other drivers are now split into sub-components (`esp_driver_gpio`, `esp_driver_rmt`, etc.) and must be listed in `REQUIRES` / `PRIV_REQUIRES` in `CMakeLists.txt`.
- `write_flash` hyphen form used in v4 (`write-flash`) still works in some contexts but `write_flash` (underscore) is the canonical v5 form; the same applies to reset flags (`default_reset`, `no_reset`, not `default-reset` / `no-reset`).

**Component Manager workflow**
- Declare dependency in `main/idf_component.yml`.
- Run `idf.py build`; the component is fetched into `managed_components/` automatically.
- Commit `idf_component.yml` and `dependencies.lock` only; ignore `managed_components/`.

**esptool connection tuning over RFC2217**
- No direct connect-timeout flag exists; use `--connect-attempts N` (`0` = infinite).
- Lower `--baud` (e.g. `115200`) gives the ROM bootloader more time to respond over a network link.
- Appending `?ign_set_control` to the RFC2217 URL relaxes control-line negotiation and avoids hangs during connect.
- On ESP32-S3 (native USB JTAG), stop OpenOCD/debug (`POST /api/debug/stop`) before flashing — serial and JTAG share the same USB interface.

**Firmware files on the Pi**
- Firmware binaries are stored at `/var/lib/rfc2217/firmware/<project>/` on the Pi.
- After build, the relevant files for flashing are: `debug-test.bin`, `bootloader/bootloader.bin`, `partition_table/partition-table.bin`, and the generated `flash_args` / `flasher_args.json` files — all under `debug-test/build/`.

**Console baud rate**
- `printf` / serial console output runs at **115200** baud (`CONFIG_ESP_CONSOLE_UART_BAUDRATE=115200`).

**ESP-IDF installation path in this devcontainer**
- ESP-IDF 5.4 lives at `/home/dev/esp/esp-idf/export.sh` (not `/opt/esp-idf`).

**Raspberry Pi Zero 2 W UART for ESP32 log monitoring**
- Use GPIO14 (TXD, physical pin 8) and GPIO15 (RXD, physical pin 10).
- For log monitoring only, wire Pi RX (GPIO15) to ESP32 TX and connect GND-to-GND.
- Default UART device without reassignment changes is `/dev/ttyS0` on GPIO14/15 (mini-UART).
- If `/dev/ttyS0` is missing, enable serial hardware and disable serial login shell via `raspi-config`, then reboot.
- Verify serial device symlinks with `ls -la /dev/serial0`.

## 26-04-05

### Session notes (flash/recovery/docs)

**Wiring and boot-mode validation (classic ESP32)**
- Confirmed BOOT pin mapping: classic ESP32 BOOT is GPIO0, reset is EN/CHIP_PU.
- Confirmed Raspberry Pi header mapping used for recovery wiring:
  - BCM17 -> physical pin 11 -> wired to ESP32 EN
  - BCM18 -> physical pin 12 -> wired to ESP32 GPIO0
- Shared GND is required; logic level must stay 3.3V.

**Workbench flashing behavior clarified**
- Normal RFC2217 flashing uses esptool control-line toggling (DTR/RTS) and can enter ROM download mode automatically when board circuitry supports it.
- `POST /api/serial/recover` is not a flash endpoint; it is a recovery/bootstrap endpoint:
  - unbinds USB,
  - drives BOOT low (when GPIO configured),
  - pulses EN,
  - rebinds USB,
  - sets slot state to `download_mode`.
- `POST /api/serial/release` releases BOOT (high-Z) and reboots to normal firmware boot.
- Practical forced sequence when auto-download is flaky:
  1. `POST /api/serial/recover`
  2. esptool flash with `--before no_reset --after no_reset`
  3. `POST /api/serial/release`

**esptool / RFC2217 details captured**
- esptool default reset modes documented: `--before default_reset`, `--after hard_reset`.
- `?ign_set_control` meaning verified from pyserial source:
  - do not wait for strict RFC2217 `SET_CONTROL` acknowledgments,
  - keep DTR/RTS toggling behavior,
  - improve compatibility with some servers.

**Documentation updates completed**
- `docs/Embedded-Workbench-FSD.md` updated to include two fallback options for unreliable auto bootloader entry:
  1. manual BOOT+RESET sequence,
  2. EN-to-GND capacitor assist (typically 1uF-10uF, often 10uF), with note that GPIO0 must still be low during reset.
- `test-firmware/README.md` improved with:
  - clearer DTR/RTS explanation,
  - typo/wording cleanup for capacitor note,
  - `ign_set_control` guidance moved into Troubleshooting,
  - "Wrong boot mode" section extended with capacitor as alternative fix.

**Operational notes from this session**
- Flash command eventually succeeded on RFC2217 (exit code 0) after timing/wiring workflow improvements.
- Venv activation reminder: use `source /workspaces/Universal-ESP32-Workbench/.venv/bin/activate` (not plain `activate`).
- UDP logging in this project: firmware sends logs to Pi UDP port 5555; portal buffers and serves via `/api/udplog`.
