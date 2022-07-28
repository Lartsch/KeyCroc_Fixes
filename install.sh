#!/bin/bash
echo -e "\n--- Starting mod installation ---"
echo -e "\nInstalling dependencies\n"
apt update
apt --yes --force-yes install hostapd
echo -e "\nOK"
echo -e "\nBacking up config (pre-mod)"
if test -f "/root/udisk/config.txt"; then
    \cp -f /root/udisk/config.txt /root/udisk/archive/config.txt.premod
    echo -e "OK. Your original config was saved up to /root/udisk/archive/config.txt.premod"
else
    echo -e "No config found for backup (pre-mod), continuing"
fi
echo -e "\nMoving files"
\cp -f modded/config.txt /root/udisk/config.txt
\cp -f modded/croc_framework /usr/local/croc/bin/croc_framework
\cp -f modded/GET /usr/local/croc/bin/GET
\cp -f modded/croc.py /usr/local/croc/croc.py
\cp -f modded/dhcpd.conf /etc/dhcp/dhcpd.conf
\cp -f modded/isc-dhcp-server /etc/default/isc-dhcp-server
echo -e "OK"
echo -e "\nSetting permissions and owner"
chmod 755 /root/udisk/config.txt /usr/local/croc/bin/croc_framework /usr/local/croc/bin/GET /usr/local/croc/croc.py
chown root:staff /usr/local/croc/bin/croc_framework /usr/local/croc/bin/GET /usr/local/croc/croc.py
chmod 644 /etc/default/isc-dhcp-server /etc/dhcp/dhcpd.conf
chown root:root /root/udisk/config.txt /etc/default/isc-dhcp-server /etc/dhcp/dhcpd.conf
echo -e "OK\n"
echo -e "--- DONE. Feel free to adjust your config now and REBOOT to apply mods. ---\n"