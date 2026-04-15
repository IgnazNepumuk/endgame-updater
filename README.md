# Endgame Firmware Updater

This repository contains a small Python script that downloads the latest firmware for the Endgame trackball from GitHub and copies it to the device when it appears as a UF2 drive.

## Requirements

- Python 3
- Internet access
- The trackball connected over USB

## Usage

Run the script with Python:

```bash
python3 update_endgame.py
```

If you need the PAW3395 firmware variant, pass `--paw3395` as an commandline argument:

```bash
python3 update_endgame.py --paw3395
```

If you want to download a specific firmware version, pass `--version <version>` as commandline argument:

```bash
python3 update_endgame.py --version 0.5.9
```

## How it works

1. Checks the latest release from `efogtech/endgame-trackball-config`
2. Downloads the matching `.uf2` firmware file
3. Waits for the trackball to appear in bootloader mode
4. Copies the firmware onto the UF2 drive

## Updating the device

1. Start the script
2. Put the trackball into reset or bootloader mode when prompted
3. Wait for the file copy to finish
4. The device should reboot automatically

## Notes

- The default command installs the normal firmware in its latest version
- The `--version <version>` argument installs a specific release
- The `--paw3395` argument installs the PAW3395 firmware (upgraded sensors)
- The script looks for common UF2 mount points on Windows, Linux, and macOS
