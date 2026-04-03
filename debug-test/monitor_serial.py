#!/usr/bin/env python3
"""
Serial monitor for ESP32 devices via RFC2217 workbench proxy.

Monitors serial output from a specific slot with optional pattern matching.

Usage:
    python3 monitor_serial.py SLOT1                          # Monitor SLOT1
    python3 monitor_serial.py SLOT1 --pattern "LOOP:"        # Match pattern
    python3 monitor_serial.py SLOT1 --timeout 30             # 30 second timeout
    python3 monitor_serial.py SLOT1 -p "LOOP:" -t 10         # Combined
"""

import serial
import time
import re
import argparse
import sys


def monitor_serial(slot="SLOT1", pattern=None, timeout=30, baudrate=115200):
    """
    Monitor serial output from an ESP32 device via RFC2217 proxy.

    Args:
        slot: Device slot (SLOT1, SLOT2, SLOT3, SLOT4)
        pattern: Optional regex pattern to match
        timeout: Monitoring timeout in seconds
        baudrate: Serial baud rate

    Returns:
        True if pattern matched (or timeout if no pattern), False otherwise
    """
    port_map = {"SLOT1": 4001, "SLOT2": 4002, "SLOT3": 4003, "SLOT4": 4004}

    if slot not in port_map:
        print(f"❌ Invalid slot: {slot}. Use SLOT1, SLOT2, SLOT3, or SLOT4")
        return False

    url = f"rfc2217://workbench.local:{port_map[slot]}"

    print(f"🔌 Connecting to {slot} ({url})...")
    try:
        ser = serial.serial_for_url(url, baudrate=baudrate, timeout=1)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

    print(f"✓ Connected. Monitoring for {timeout}s", end="")
    if pattern:
        print(f" (pattern: '{pattern}')")
    else:
        print()

    start = time.time()
    matched = False
    line_count = 0

    try:
        while time.time() - start < timeout:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        line_count += 1
                        timestamp = time.strftime("%H:%M:%S")
                        print(f"[{timestamp}] {line}")

                        # Check pattern if provided
                        if pattern:
                            if re.search(pattern, line):
                                print(f"✓ Pattern matched: '{pattern}'")
                                matched = True
                                break
                except UnicodeDecodeError:
                    pass
            else:
                time.sleep(0.01)  # Avoid busy waiting

    except KeyboardInterrupt:
        print("\n⏹ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        ser.close()

    elapsed = time.time() - start
    print(f"\n📊 Received {line_count} lines in {elapsed:.1f}s")

    if pattern and not matched:
        print(f"⚠ Pattern not found within timeout")
        return False

    return True


def main():
    """Command-line interface for serial monitoring."""
    parser = argparse.ArgumentParser(
        description="Monitor ESP32 serial output via workbench RFC2217 proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 monitor_serial.py SLOT1
  python3 monitor_serial.py SLOT1 --pattern "LOOP:"
  python3 monitor_serial.py SLOT1 --timeout 60 --baudrate 115200
  python3 monitor_serial.py SLOT2 -p "WiFi connected" -t 30
  python3 monitor_serial.py SLOT3 -p "LOOP:" -t 10
  python3 monitor_serial.py SLOT4 -p "BOOT" -t 5
        """,
    )

    parser.add_argument(
        "slot",
        nargs="?",
        default="SLOT1",
        choices=["SLOT1", "SLOT2", "SLOT3", "SLOT4"],
        help="Device slot (default: SLOT1)",
    )

    parser.add_argument(
        "-p", "--pattern", help="Regex pattern to match (stops on match)"
    )

    parser.add_argument(
        "-t", "--timeout", type=int, default=30, help="Timeout in seconds (default: 30)"
    )

    parser.add_argument(
        "-b", "--baudrate", type=int, default=115200, help="Baud rate (default: 115200)"
    )

    args = parser.parse_args()

    success = monitor_serial(
        slot=args.slot,
        pattern=args.pattern,
        timeout=args.timeout,
        baudrate=args.baudrate,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
