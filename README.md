# BIGTREETECH_MMS

### G-Code Commands

**Filament Loading & Swapping:**

| Command | Arguments (Defaults) | Description |
|---|---|---|
| `MMS_CHARGE` | `SLOT` (int, required) | Load filament into the heated extruder gears and sync (ready to print). |
| `MMS_CAREFUL_CHARGE` | `SLOT` (int, required) | Carefully engage filament into the extruder gears. |
| `MMS_EJECT` | None | Extract filament from heated extruder gears and retract it back to the MMS. |
| `MMS_EJECT_UNSELECT` | None | Eject filament and unselect the slot. |
| `MMS_LOAD` | `SLOT` (int, req), `WAIT` (0/1, def: 0) | Move filament up to the toolhead sensor (does not enter extruder gears). |
| `MMS_UNLOAD` | `SLOT` (int, opt), `WAIT` (0/1, def: 0) | Unload filament from the toolhead sensor back to the MMS. |
| `MMS_PRE_LOAD` | `SLOT` (int, required) | Pre-load filament into the MMS buffer path. |
| `MMS_TRAY_EJECT` | None | Eject filament from the purge tray. |

**MMS Motion & Control:**

| Command | Arguments (Defaults) | Description |
|---|---|---|
| `MMS_SELECT` | `SLOT` (int, req), `WAIT` (0/1, def: 0) | Move the selector to a specific slot. |
| `MMS_UNSELECT` | `WAIT` (0/1, def: 0) | Move the selector away from the slots. |
| `MMS_SLOT_EXTRUDER_SYNC` | `SLOT` (int, required) | Turn on stepper synchronization between the MMS drive and the toolhead extruder. |
| `MMS_SLOT_EXTRUDER_UNSYNC` | `SLOT` (int, required) | Turn off stepper synchronization. |
| `MMS_STOP` | `SLOT` (int, optional) | Abort the current MMS operation. |
| `MMS_MOVE` | `SLOT` (int, req), `DISTANCE` (float, req), `SPEED` (float, opt) | Move MMS motors manually. |
| `MMS_DRIP_MOVE` | `SLOT` (int, required) | Perform a drip move with MMS motors. |
| `MMS_POP` | `SLOT` (int, opt), `WAIT` (0/1, def: 0) | Pop the filament out of the slot. |

**Buffer Management:**

| Command | Arguments (Defaults) | Description |
|---|---|---|
| `MMS_BUFFER_ACTIVATE` | `EXTEND` (int, def: 0) | Activate the buffer monitor for the active slot. |
| `MMS_BUFFER_DEACTIVATE` | `EXTEND` (int, def: 0) | Deactivate the buffer monitor. |
| `MMS_BUFFER_MEASURE` | `SLOT` (int, req), `FORCE` (0/1, def: 0) | Measure the current buffer state. |
| `MMS_BUFFER_FILL` | `SLOT` (int, required) | Fill the buffer loop with filament. |
| `MMS_BUFFER_CLEAR` | `SLOT` (int, required) | Clear the buffer loop. |
| `MMS_BUFFER_HALFWAY` | `SLOT` (int, required) | Move the buffer loop to the halfway position. |

**Slot Configuration & Metadata:**

| Command | Arguments (Defaults) | Description |
|---|---|---|
| `MMS_SLOT_COLOR` | `SLOT` (int, req), `COLOR` (str) | Set the filament color for a slot. |
| `MMS_SLOT_MATERIAL` | `SLOT` (int, req), `MATERIAL` (str) | Set the filament material for a slot. |
| `MMS_SLOT_SPOOL` | `SLOT` (int, req), `SPOOL_ID` (int) | Link a Spoolman spool ID to a slot. |
| `MMS_SLOT_META` | `SLOT` (int, req), `KEY` (str), `VALUE` (str) | Read or write general metadata for a slot. |
| `MMS_SLOT_META_TRUNCATE` | `SLOT` (int, optional) | Clear metadata for a slot. |
| `MMS_SLOT_MAP` | `MAP` (string) | Map physical slots to logical slots. |
| `MMS_LANE_DATA_PULL` | `LANE` (int) | Pull lane data configurations. |

**RFID Integration:**

| Command | Arguments (Defaults) | Description |
|---|---|---|
| `MMS_RFID_DETECT` | `SWITCH` (0/1, def: 0) | Detect presence of RFID tags. |
| `MMS_RFID_READ` | `SLOT` (int, req), `SWITCH` (0/1, def: 1), `ALIGN` (0/1, def: 1) | Read data from an RFID tag. |
| `MMS_RFID_WRITE` | `SLOT` (int, req), `DATA` (str, def: "{}"), `ALIGN` (0/1, def: 1), `SPOOLID` (int, opt) | Write data to an RFID tag. |
| `MMS_RFID_TRUNCATE` | `SLOT` (int, optional) | Clear data from an RFID tag. |
| `MMS_RFID_RESET` | None | Reset the RFID module. |

**Status, Calibration & Diagnostics:**

| Command | Arguments (Defaults) | Description |
|---|---|---|
| `MMS_STATUS` | None | Display the overall status of the MMS. |
| `MMS_STATUS_STEPPER` | None | Display the status of the MMS steppers. |
| `MMS_SAMPLE` | None | Sample MMS states for diagnostics. |
| `MMS_SAMPLE_STEPPER` | None | Sample MMS stepper states for diagnostics. |
| `MMS_BOWDEN_CALIBRATION` | None | Run the Bowden tube calibration sequence. |
| `MMS_SLOTS_CHECK` | None | Check the filament path for all slots. |
| `MMS_SLOTS_CHECK_LOOP` | None | Continuously check the filament path for all slots. |
| `MMS_SLOTS_WALK` | None | Sequentially walk through all slots. |
| `MMS_SLOTS_LOOP` | None | Continuously loop through all slots. |
| `MMS_TEST_SELECTOR` | `SLOT` (int, required) | Run a diagnostic test on the selector. |
| `MMS_TEST_SELECTOR_MEASURE`| `SLOT` (int, req) | Test and measure selector capabilities. |
| `MMS_TEST` / `MMS_D_TEST`| None | Internal testing and debug commands. |
| `MMS_MAN` | Various | Manual MMS stepper control for debug. |
| `MMS_LOG` | `LEVEL` (string, optional) | Dump MMS logs to the console. |
| `MMS_DRYER_START` | `LANE` (int, opt), `TEMP` (int, opt), `TIME` (int, opt) | Control the integrated filament dryer. |
| `MMS_DRYER_STOP` | `LANE` (int, optional) | Stop the integrated filament dryer. |
| `MMS_AUTOLOAD_ENABLE` | None | Enable the autoload feature. |
| `MMS_AUTOLOAD_DISABLE` | None | Disable the autoload feature. |

*(Note: Some UI-facing commands also include a `_U` variant, e.g. `MMS_LOAD_U` or `MMS_PREPARE_U`, which are aliases used internally for the touchscreen UI to safely execute commands asynchronously without locking the UI.)*

**Filament Processing & Accessories:**

| Command | Arguments (Defaults) | Description |
|---|---|---|
| `MMS_CUT` | None | Perform a filament cut. |
| `MMS_SIMPLE_CUT` | None | Perform a simple filament cut. |
| `MMS_PURGE` | None | Purge filament into the tray. |
| `MMS_PURGE_TEST` | None | Test the purge mechanism. |
| `MMS_TRAY` | None | Move the tray. |
| `MMS_BRUSH` | None | Use the wipe brush. |
| `MMS_BRUSH_PECK` | None | Peck the wipe brush. |
| `MMS_BRUSH_WIPE` | None | Wipe on the brush. |

**Advanced System Actions:**

| Command | Arguments (Defaults) | Description |
|---|---|---|
| `MMS_SPOOLMAN` | `SYNC`, `REFRESH`, `FIX`, `CLEAR`, `SPOOLINFO`, `QUIET` | Interact with the Spoolman integration. |
| `MMS_SWAP_MAPPING` | `SWAP_NUM` (int) | Map a swap operation. |
| `MMS_SWAP_MAPPING_RESET` | None | Reset the swap mapping. |
| `MMS_PAUSE` | None | Pause the current MMS operation. |
| `MMS_RESUME` | None | Resume the paused MMS operation. |
| `MMS_DRIPLOAD` | `SWITCH` (int) | Manage drip loading. |
| `MMS_PREPARE` | None | Prepare MMS system. |

### Compatibility
* Klipper: compatible between [Commits on Nov 27, 2025: stm32: f0 i2c clean nackcf interrupt on handle](https://github.com/Klipper3d/klipper/commit/938300f3c3cc25448c499a3a8ca5b47b7a6d4fa8) and the lastest version [Commits on Apr 16, 2026: polar: add velocity scaling (#7172)](https://github.com/Klipper3d/klipper/commit/373f200ca69adb624675f42e685f61d85d49ba40). The stepper scheduling uses the newly updated `motion_queuing.py` upstream of Klipper, so it is necessary to use the new version of Klipper.
* KlipperScreen: compatible between [Commits on Sep 12, 2025: refactor: less logging when on battery](https://github.com/KlipperScreen/KlipperScreen/commit/b3115f9b9b329642d4dbf0ad225ab065ea3eda80) and the lastest version [Commits on Apr 5, 2026: Revert "feat: Add an option to add the remaining spool weight to the title-bar (#1662)"](https://github.com/KlipperScreen/KlipperScreen/commit/056831910087a858908f9f5d117ad5c50446e729). In theory, earlier KlipperScreen also supports it, but it has not been actually tested yet.
* Python: Only supports Klipper for Python 3 environment.

### Installation
* Download installation script.

    ```
    cd ~
    git clone https://github.com/bigtreetech/BIGTREETECH_MMS.git
    cd ~/BIGTREETECH_MMS
    ```
* Start Installation

    ```
    ./install.sh
    ```

    Running supports the following parameters: 

    ```
    [-h] [-i] [-d] [-u] [-z] [-g]
    ```

    * `-h`: help

    * `-i`: install

    * `-d`: uninstall

    * `-u`: update klipper and KlipperScreen. all parameters in the configuration files will be automatically copied from the old configuration without user interaction.

    * `-z`: skip github update check. The script will automatically check the version on GitHub by default and ensure that it runs with the latest version. If you have modified some logic of script locally, please disable updates at runtime through the `-z` parameter. For example:

        * Do not update installation: `./install.sh -z` or`./install.sh -zi`

        * Do not update uninstallation: `./install.sh -zd`

    * `-g`: get version

    * no flags for default `-i` install

### Flash
Both ViViD and Buffer MCU have built-in [Katapult (formerly known as CanBoot)](https://github.com/Arksine/katapult) for updating Klipper firmware.

We recommend using the `flash.sh` script provided here to update the firmware of ViViD and Buffer, rather than directly using the Katapult command, as there will be an additional step to verify the binary content of the firmware, try to avoid startup issues caused by flashing incorrect firmware as much as possible.

`flash.sh` will list devices with serial id containing `vivid` or `buffer`, select the device ID we want to flash to start flashing. If no parameter are included, the [factory firmware](./firmware/) will be flashed by default. We can also specify the binary file to be flashed through the `-f` parameter.

for example:

* `flash.sh`
* `flash.sh -f ~/klipper/out/klipper.bin`

### Config
Please refor to [mms_config](./docs/en/mms_config.md) for details.

### ChangeLog
Please refor to [mms_changelog](./docs/en/mms_changelog.md) for details.

### Moonraker Update Manager
To keep BIGTREETECH_MMS up to date directly from your Mainsail/Fluidd web interface, add the following block to your `moonraker.conf`:

```ini
[update_manager bigtreetech_mms]
type: git_repo
path: ~/BIGTREETECH_MMS
origin: https://github.com/bigtreetech/BIGTREETECH_MMS.git
managed_services: klipper moonraker
primary_branch: main
install_script: update.sh
```

### 🐇 Acknowledgements
The script implementation referenced the logic and some source code from the excellent project [Happy-Hare](https://github.com/moggieuk/Happy-Hare) and [AFC](https://github.com/ArmoredTurtle/AFC-Klipper-Add-On).

Thanks to the open source community for creating such valuable resources, so we are able to build upon.
