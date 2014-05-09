#!/usr/bin/python
#
#  imported from project Mintstick, by Clement Lefebvre
#
#  Copyright (C) 2013 THE isodumper'S COPYRIGHT HOLDER
#  This file is distributed under the same license as the isodumper package.
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
#  Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.
#
#  Author isodumper software= papoteur <papoteur@mageialinux-online.org>

import os, sys
import getopt
import parted
from subprocess import call

sys.path.append('/usr/lib/isodumper')

def do_umount(target):
        mounts = get_mounted(target)
        if mounts:
            print 'Unmounting all partitions of '+target+':'
        for mount in mounts:
            print 'Trying to unmount '+mount[0]+'...'
            try:
                retcode = call('umount '+mount[0], shell=True)
                if retcode < 0:
                    print 'Error, umount '+mount[0]+' was terminated by signal '+str(retcode)
                    sys.exit(6)
                else:
                    if retcode == 0:
                        print mount[0]+' successfully unmounted'
                    else:
                        print 'Error, umount '+mount[0]+' returned '+str(retcode)
                        sys.exit(6)
            except OSError, e:
                print 'Execution failed: '+str(e)
                sys.exit(6)


def get_mounted(target):
        try:
            lines = [line.strip("\n").split(" ") for line in open ("/etc/mtab", "r").readlines()]
            return [mount for mount in lines if mount[0].startswith(target)]
        except:
             print 'Could not read mtab !'
             sys.exit(6)

def raw_format(device_path, fstype, volume_label, uid, gid):
  
    do_umount(device_path)
    
    # First erase MBR and partition table , if any
    os.system ("dd if=/dev/zero of=%s bs=512 count=1 >/dev/null 2>&1" % device_path)
    
    device = parted.getDevice(device_path)
    
    # Create a default partition set up                        
    disk = parted.freshDisk(device, 'msdos')
    disk.commit()
    regions = disk.getFreeSpaceRegions()    

    if len(regions) > 0:
        #print "Build partition"
        # Define size
        start = parted.sizeToSectors(1, "MiB", device.sectorSize)
        #print "start %s" % start
        end = device.getLength() - start - 1024
        #print end
        
        # Alignment
        #cylinder = device.endSectorToCylinder(end)
        #end = device.endCylinderToSector(cylinder)
        #print end
        try:
            geometry = parted.Geometry(device=device, start=start, end=end)
        except:
            print "Geometry error - Can't create partition"
            sys.exit(5)
        
        # fstype
        fs = parted.FileSystem(type=fstype, geometry=geometry)
        
        # Create partition
        partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL, geometry=geometry, fs=fs)
        constraint = parted.Constraint(exactGeom=geometry)
        disk.addPartition(partition=partition, constraint=constraint)
        disk.commit()
        
        # Format partition according to the fstype specified
        if fstype == "fat32":
            os.system("mkdosfs -F 32 -n \"%s\" %s >/dev/null 2>&1" % (volume_label, partition.path))
        if fstype == "ntfs":
            os.system("mkntfs -f -L \"%s\" %s >/dev/null 2>&1" % (volume_label, partition.path))
        elif fstype == "ext4":
            os.system("mkfs.ext4 -E root_owner=%s:%s -L \"%s\" %s >/dev/null 2>&1" % (uid, gid, volume_label, partition.path))
    sys.exit(0)





def main():
    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd:f:l:u:g:", ["help", "device=","filesystem=","label=","uid=","gid="])
    except getopt.error, msg:
        print msg
        print "for help use --help"
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            print "Usage: %s -d device -f filesystem -l volume_label\n"  % sys.argv[0]
            print "-d|--device          : device path"
            print "-f|--filesystem      : filesystem\n"
            print "-l|--label           : volume label\n"
            print "-u|--uid             : uid of user\n"
            print "-g|--gid             : gid of user\n"
            print "Example : %s -d /dev/sdj -f fat32 -l \"USB Stick\" -u 1000 -g 1000" % sys.argv[0]
            sys.exit(0)
        elif o in ("-d"):
            device = a
        elif o in ("-f"):
            if a not in [ "fat32", "ntfs", "ext4" ]:
                print "Specify fat32, ntfs or ext4"
                sys.exit(3)
            fstype = a
        elif o in ("-l"):
            label = a
        elif o in ("-u"):
            uid = a
        elif o in ("-g"):
            gid = a
    
    argc = len(sys.argv)
    if argc < 11:
      print "Too few arguments"
      print "for help use --help"
      exit(2)
    
    raw_format(device, fstype, label, uid, gid)
    
if __name__ == "__main__":
    main()
