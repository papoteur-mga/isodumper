#!/bin/sh
#
#    Copyright 2007-2009 Canonical Ltd.
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA

LIBFILES="isodumper.py find_devices"
DATAFILES="isodumper.glade header.png"


if [ "$1" = "uninstall" ]; then
    rm -rf /usr/lib/isodumper
    rm -rf /usr/share/isodumper
    rm -r /usr/share/applications/isodumper.desktop
    rm -f /usr/bin/isodumper
else
    cp share/applications/isodumper.desktop /usr/share/applications/
    cp isodumper /usr/bin/
    mkdir -p /usr/lib/isodumper
    mkdir -p /usr/share/isodumper

    for item in $LIBFILES; do
        cp lib/$item /usr/lib/isodumper/
    done

    for item in $DATAFILES; do
        cp share/usb-isodumper/$item /usr/share/isodumper/
    done
fi
