# KeyCroc_Fixes
- Some fixes for the shi**y KeyCroc firmware/framework that has a lot of bugs.  
- Some additional features (see below...)  
- Some detailed notes on the KeyCroc's payload execution behavior that come too short in official docs.  
Most of this is done dirty. Make sure to create pull requests if you care to improve it. Made this mid 2021 and forgot about it, now remembered and thought I'd just upload it. I do not plan to work on this regularly.

#### Note: Only use this if you need it / know what you are doing. Run diff with the original files if you need to see the changes made / for your safety. If you mess up your device and point at me, I **will** laugh at you.

 1. [Installation](#installation)
 2. [Included mods](#included-mods)
    - [CrocAP](#crocap)
	- [Matchless payloads fix](#matchless-payloads-fix)
 	- [Environment variables fix](#environment-variables-fix)
	- [Auto-Attackmode option](#auto-attackmode-option)
	- [Disable matchless](#disable-matchless)
	- [Other changes](#other-changes)
 	- *More to come! (probably not)*

## Installation

### Quick setup for modded framework

NOTE: Backups are good

1. Make sure your Key Croc uses the firmware 1.3-stable from 2020-06-26, if not, download and install the update as described in the Quick Start Guide
2. Download the required files
    - Complete directory modded/
    - install.sh
3. Enter arming mode on the Key Croc by plugging it in, waiting for 10-15 seconds and then pressing the hidden button with a SIM tool or similar - your notebook should show the KeyCroc udisk as a normal USB storage device after a few seconds and the LED will blink blue
4. Move the downloaded files:
    - modded/ folder + install.sh --> udisk/archive/
5. Edit the config.txt in the udisk root to connect your Key Croc to the internet using your local WiFi or by hosting a hotspot from your phone:
    - Edit `WIFI_SSID` and `WIFI_PASS` correspondingly
    - Make sure that `SSH` is set to `ENABLE`
    - Securely eject the Key Croc
    - Re-plug it and wait for it to connect to your Wifi AP
    - DO NOT enter arming mode this time
6. Connect to your Key Croc via SSH
    - Find out the local IP of the Key Croc, for ex. by looking for the connected devices on your router
    - Make sure the device you want to start the SSH connection from is in the same network as the KeyCroc
    - Use Putty or another SSH client with the Key Croc's local IP as host and 22 as port
    - Use the default credentials to log in: `root|hak5croc`
7. Run the following commands:
    - `cd /root/udisk/archive`
    - `find . -type f -exec sed -i 's/\r$//' {} +`  
    *(this makes sure that all downloaded files use Unix EOL, in case they were transferred from Windows)*
    - `chmod +x install.sh`
    - `./install.sh`
8. OPTIONAL: If you plan to use Metasploit, Responder or impacket, run the command `INSTALL_EXTRAS`
9. If needed, you can proceed with adjustments to your config.txt
    - Either do it without arming mode via SSH, in this case the config resides in /root/udisk/config.txt
    - Or enter arming mode and edit the config.txt (secure eject afterwards) from the mounted udisk drive as usual
10. Re-plug the Key Croc to apply changed configurations and mods

## Included mods

### CrocAP
This firmware modification enables you to host a WiFi AP on your Key Croc. Main use case is to be able as an actor to connect to the Key Croc anytime you are in reach and access its shell.
#### Configuration
This mod shares its configuration file with the other Key Croc options, so you need to edit the config.txt file found on the  udisk.

 - Get started by setting `WIFI_AP ENABLED` (default is DISABLE). When
   set, WIFI_SSID and WIFI_PASS options are used to host an access point
   instead for connecting to one. If you want an open (unprotected) AP,
   omit the WIFI_PASS setting. Take care of escaping like usual.
 - You can choose to hide the SSID of the AP (prevent broadcasting) by
   setting `WIFI_HIDE_AP ENABLE` (default is DISABLE).

Refer to the example configuration which is uploaded here for more information.
#### Usage
1.  Build and save your config.txt file
2.  Re-plug the Key Croc
3.  LED will start blinking yellow  during AP setup
4.  LED will blink red when setup fails due to a missing installation of hostapd
5.  LED will blink green when the setup seems to be successful – turns white after a few seconds
6.  Now check if you can connect to the AP
	- If you can’t see your AP you might have set WIFI_HIDE_AP to ENABLED from the config, enter the SSID manually in this case.
7.  Once connected to the AP from a device of your choice, you can connect to Key Croc’s shell via SSH by using the gateway IP as host IP, default port 22 and the usual credentials.

**NOTES:**
- When switching to or from an ethernet attack mode while hosting an AP, the clients sometimes may have to reconnect
- The gateway address is 172.16.32.1, subnet /24
- DHCP range is 172.16.32.3-99
- Right after booting there might be too little entropy for the first client to connect, try again after a minute
- As far as I know, you can NOT use the wifi module in AP and client mode simultaneously
- There might be issues with using some attack modes when in AP mode, need to look into this

It takes about 60 seconds from plugging in the Key Croc to being able to connect to the AP.
### Matchless payloads fix
This firmware modification fixes the badly implemented matchless payload detection which is used to run them on boot of the Key Croc. The original implementation did not execute payloads reliably and did also not consider MATCH lines that are commented out with “#”. Using this mod, the behavior is as expected: Matchless payloads run when present and lines starting with “#” (comments) and also combinations where whitespace is used before the MATCH command, either with or without “#”, are taken account for.
#### Configuration
No configuration needed.
#### Usage
Write matchless payloads just like described in the official docs. Simply omit any MATCH commands or comment them out with # for the payload to run on boot. **Also note the following considering the execution of payloads using these framework mods. Also applies to some of the weird stock behaviour:**
- MATCHLESS + AUTO_ATTACKMODE ENABLE + KEYBOARD: No need to set the attack mode to HID in the payload. Keyboard specs will be cloned as long as no overwrite is present in config.txt and the keyboard is plugged in before the Key Croc boots.
- MATCHLESS + AUTO_ATTACKMODE DISABLE + KEYBOARD: You need to set the attack mode to HID in the payload. Keyboard specs will still be written to /tmp/vidpid on boot as long as no overwrite is present in config.txt and the keyboard is plugged in before the Key Croc boots. You can read that file from your payloads to reutilize.
- MATCHLESS + AUTO_ATTACKMODE ENABLE + NO KEYBOARD: No need to set the attack mode to HID in the payload. Keyboard specs will be the defaults though (ATTACKMODE HID without options); can be overwritten from config.txt.
- MATCHLESS + AUTO_ATTACKMODE DISABLE + NO KEYBOARD: You need to set the attack mode to HID in the payload. Overwriting from config.txt will not have any effect
- MATCH BASED + AUTO_ATTACKMODE ENABLE: No need to set the attack mode to HID in the payload. Cloned keyboard specs will be used.
- MATCH BASED + AUTO_ATTACKMODE DISABLE: You need to set the attack mode to HID in the payload. Keyboard specs will still be written to /tmp/vidpid on boot as long as no overwrite is present in config.txt and the keyboard is plugged in before the Key Croc boots. You can read that file from your payloads to reutilize.
- Generally, if using AUTO_ATTACKMODE ENABLE, I recommend not adding an additional ATTACKMODE command in the payload, since this will trigger another device reconnect (which is more obvious / less stealth)
- Defining custom hardware properties from the config.txt file (not via ATTACKMODE command options) will prevent cloning on boot at all
- Having a keyboard attached and setting `ATTACKMODE HID` in the payload manually without specifying properties, you will erase the cloned properties and use defaults. To change mode and keep cloned settings, read out /tmp/vidpid and use the returned values for the ATTACKMODE options

### Environment variables fix
This firmware modification fixes the poorly implemented setup of environment variables on boot. Several variables are not set properly, the most important among them being DUCKY_LANG. This leads to issues, for example when using QUACK STRING without setting DUCKY_LANG manually. The command reads the language from the environment variable DUCKY_LANG and defaults to US layout if not found, causing issues in payloads.

The mod does the following:
 - Read in from config.txt and export DUCKY_LANG variable on boot (croc_framework), also add it to /root/.profile to have it set in interactive shell sessions.
 - Read and export DUCKY_LANG on matched payload execution to the payload's child process
 - Source and export the GET function to support `GET <VAR>` in matchless payloads
#### Configuration
No configuration needed.
#### Usage
Using this mod, you can access the DUCKY_LANG value from any payload, script or interactive shell. Using `QUACK STRING` also works without any further considerations. You are also able to use `GET [var]` in matchless payloads. The main advantage is a) not needing to set it manually in each payload, b) managing the language only from config.txt (if wanted) and c) building universal payloads that read DUCKY_LANG and decide which keys to inject based on that.

*Alternatively, you could always do `export DUCKY_LANG=xx` in a payload or your shell session to fix issues with `QUACK STRING`. You can also source GET manually in a payload with `source /usr/local/croc/bin/GET` and then use the GET function.*

### Auto-Attackmode option
This one gives you another option for the config.txt file that allows you to enable or disable automatically starting `ATTACKMODE HID` on boot.
#### Configuration
This mod shares its configuration file with the other Key Croc options, so you need to edit the config.txt file found in udisk.
Simply set `AUTO_ATTACKMODE ENABLE` to  automatically booting into `ATTACKMODE HID` mode (default is DISABLE).
Refer to the example configuration which is uploaded here for more information.
#### Usage
Nothing further to do. Some notes though:
- This setting applies to matchless AND match based payloads
- If AUTO_ATTACKMODE is disabled, you always need to manually set it in your payloads
- If AUTO_ATTACKMODE is disabled, VID/PID are still read if a keyboard is present and saved to /tmp/vidpid for usage in payloads (as long as not overwritten from config.txt, then no detection takes place)
- If AUTO_ATTACKMODE is enabled and you ONLY need HID as attack mode, then it is best not to include any further ATTACKMODE command in your payload since it triggers another device reconnect, being more noticeable

### Disable matchless
This firmware modification is mostly a debugging feature to disable matchless payloads from running on boot of the Key Croc, which is sometimes useful if you want to run them manually from a shell.
#### Configuration
This mod shares its configuration file with the other Key Croc options, so you need to edit the config.txt file found in udisk.
Simply set `MATCHLESS DISABLE` to disable autorun on boot for any present matchless payloads (default is ENABLE).
Refer to the example configuration which is uploaded here for more information.
#### Usage
Nothing further to do.

### Other changes
Several other small adjustments have been made.

**Payload execution behaviour**
 - Matchless payloads will run one after another, not at the same time (this prevents interference of ATTACKMODE when multiple matchless payloads are in place - ususually though, there would only be one matchless payload at a time)
 - Key parsing will start only after all matchless payloads have been finished, so match based payloads do not interfer with matchless ones if triggered too early
 - The VID/PID detection is tried once (even with AUTO_ATTACKMODE disabled) before matchless payloads are run (waits 3 seconds), then runs the payloads and afterwards starts the default detection loop for match based payloads.

Things might change... just because it works good for me doesn't mean it works good for u. This is custom to my needs.

***Based on firmware 1.3-stable (2020-06-26)***
