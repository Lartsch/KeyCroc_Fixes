#!/bin/bash
echo -e "\n--- Starting mod uninstallation ---"
echo -e "\nRemoving installed dependencies\n"
apt --yes --force-yes purge hostapd
apt-get --yes --force-yes autoremove
echo -e "\nOK"
echo -e "\nBacking up modded config (post-mod)"
if test -f "/root/udisk/config.txt"; then
    \cp -f /root/udisk/config.txt /root/udisk/archive/config.txt.postmod
    echo -e "OK, modded config file backed up as /root/udisk/archive/config.txt.postmod"
else
    echo -e "No config found (post-mod), not backing up"
fi
echo -e "\nRestoring original config (pre-mod)"
if test -f "/root/udisk/archive/config.txt.premod"; then
    \cp -f /root/udisk/archive/config.txt.premod /root/udisk/config.txt
    echo -e "OK, original config file restored (pre-mod)"
else
    \cp -f original/config.txt_original /root/udisk/config.txt
    echo -e "No backup of original config found (pre-mod), used default config instead"
fi
echo -e "\nMoving files"
\cp -f original/croc_framework_original /usr/local/croc/bin/croc_framework
\cp -f original/GET_original /usr/local/croc/bin/GET
\cp -f original/croc.py_original /usr/local/croc/croc.py
\cp -f original/dhcpd.conf_original /etc/dhcp/dhcpd.conf
\cp -f original/isc-dhcp-server_original /etc/default/isc-dhcp-server
echo -e "OK"
echo -e "\nSetting permissions and owner"
chmod 755 /root/udisk/config.txt /usr/local/croc/bin/croc_framework /usr/local/croc/bin/GET /usr/local/croc/croc.py
chown root:staff /usr/local/croc/bin/croc_framework /usr/local/croc/bin/GET /usr/local/croc/croc.py
chmod 644 /etc/default/isc-dhcp-server /etc/dhcp/dhcpd.conf
chown root:root /root/udisk/config.txt /etc/default/isc-dhcp-server /etc/dhcp/dhcpd.conf
echo -e "OK\n"
echo -e "--- DONE. Feel free to adjust your config now and REBOOT to apply mods. ---\n"