#!/usr/bin/python
#
#  Copyright (c) 2007-2009 Canonical Ltd.
#
#  Author: Oliver Grawert <ogra@ubuntu.com>
#
#  Modifications 2013 from papoteur <papoteur@mageialinux-online.org>
#  and Geiger David <david.david@mageialinux-online.org>
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

#  Requires python-parted

import gtk
import gtk.glade
import gobject
import os, re
import io
import gettext
from gettext import gettext as _
from subprocess import call, Popen, PIPE
import time
import dbus


class NoUDisks2(Exception):
    pass


class UDisks2(object):

    BLOCK = 'org.freedesktop.UDisks2.Block'
    FILESYSTEM = 'org.freedesktop.UDisks2.Filesystem'
    DRIVE = 'org.freedesktop.UDisks2.Drive'

    def __init__(self):
        self.bus = dbus.SystemBus()
        try:
            self.bus.get_object('org.freedesktop.UDisks2',
                        '/org/freedesktop/UDisks2')
        except dbus.exceptions.DBusException as e:
            if getattr(e, '_dbus_error_name', None) == 'org.freedesktop.DBus.Error.ServiceUnknown':
                raise NoUDisks2()
            raise

    def node_mountpoint(self,node):

        def de_mangle(raw):
            return raw.replace('\\040', ' ').replace('\\011', '\t').replace('\\012',
                    '\n').replace('\\0134', '\\')

        for line in open('/proc/mounts').readlines():
            line = line.split()
            if line[0] == node:
                return de_mangle(line[1])
        return None

    def device(self, device_node_path):
        device_node_path = os.path.realpath(device_node_path)
        devname = device_node_path.split('/')[-1]

        # First we try a direct object path
        bd = self.bus.get_object('org.freedesktop.UDisks2',
                        '/org/freedesktop/UDisks2/block_devices/%s'%devname)
        try:
            device = bd.Get(self.BLOCK, 'Device',
                dbus_interface='org.freedesktop.DBus.Properties')
            device = bytearray(device).replace(b'\x00', b'').decode('utf-8')
        except:
            device = None

        if device == device_node_path:
            return bd

        # Enumerate all devices known to UDisks2
        devs = self.bus.get_object('org.freedesktop.UDisks2',
                        '/org/freedesktop/UDisks2/block_devices')
        xml = devs.Introspect(dbus_interface='org.freedesktop.DBus.Introspectable')
        for dev in re.finditer(r'name=[\'"](.+?)[\'"]', type(u'')(xml)):
            bd = self.bus.get_object('org.freedesktop.UDisks2',
                '/org/freedesktop/UDisks2/block_devices/%s2'%dev.group(1))
            try:
                device = bd.Get(self.BLOCK, 'Device',
                    dbus_interface='org.freedesktop.DBus.Properties')
                device = bytearray(device).replace(b'\x00', b'').decode('utf-8')
            except:
                device = None
            if device == device_node_path:
                return bd

        raise ValueError(_('%r not known to UDisks2')%device_node_path)

    def find_devices(self):
        proxy = self.bus.get_object("org.freedesktop.UDisks2", "/org/freedesktop/UDisks2")
        iface = dbus.Interface(proxy, "org.freedesktop.UDisks2")
        _udisks2_obj_manager = dbus.Interface(iface, "org.freedesktop.DBus.ObjectManager")
        objects=_udisks2_obj_manager.GetManagedObjects()
        re_drive = re.compile('(?P<path>.*?/drives/(?P<id>.*))')
        re_block = re.compile('(?P<path>.*?/block_devices/(?P<id>.*))')
        devs= [m.groupdict() for m in
                     [re_drive.match(path) for path in objects.keys()]
                 if m]
        blocks = [m.groupdict() for m in
                     [re_block.match(path) for path in objects.keys()]
                 if m]
        list=[]

        for dev in devs:
            dev_obj =objects[dev['path']]['org.freedesktop.UDisks2.Drive']
            if (dev_obj['ConnectionBus'] == 'usb' or dev_obj['ConnectionBus'] == 'sdio') and \
                 (dev_obj['Removable'] == 1 or dev_obj['MediaRemovable'] == 1 ):
               item=[]
               vend = dev_obj['Vendor']
               name = dev_obj['Model']
               for block in blocks:
                   if dev['path'] == objects[block['path']]['org.freedesktop.UDisks2.Block']['Drive']:
                       path = '/dev/'+block['path'].split('/')[-1]
               size = dev_obj['Size']
               item.append(vend+" "+name)
               item.append(path)
               item.append(size)
               list.append(item)
        return list

    def mount(self, device_node_path):
        try:
            d = self.device(device_node_path)
            mount_options = ['rw', 'noexec', 'nosuid',
                'nodev', 'uid=%d'%os.geteuid(), 'gid=%d'%os.getegid()]
            r=d.Mount(
                {
                    'auth.no_user_interaction':True,
                    'options':','.join(mount_options)
                },
                dbus_interface=self.FILESYSTEM)
            return unicode(r)
        except:
            # May be already mounted, check
            mp = self.node_mountpoint(str(device_node_path))
            print mp, sys.exc_info()[0]
            if mp is None:
                raise ValueError(sys.exc_info()[0])
            return mp

    def unmount(self, device_node_path):
        d = self.device(device_node_path)
        d.Unmount({'force':True, 'auth.no_user_interaction':True},
                dbus_interface=self.FILESYSTEM)

    def drive_for_device(self, device):
        drive = device.Get(self.BLOCK, 'Drive',
            dbus_interface='org.freedesktop.DBus.Properties')
        return self.bus.get_object('org.freedesktop.UDisks2', drive)

    def eject(self, device_node_path):
        drive = self.drive_for_device(self.device(device_node_path))
        drive.Eject({'auth.no_user_interaction':True},
                dbus_interface=self.DRIVE)

def countFiles(directory):
    files = []
    if os.path.isdir(directory):
        for path, dirs, filenames in os.walk(directory):
            files.extend(filenames)
    return len(files)

def makedirs(dest):
    if not os.path.exists(dest):
        os.makedirs(dest)

class IsoDumper:
    def __init__(self,user):
        APP="isodumper"
        DIR="/usr/share/locale"
        RELEASE="v0.40"

        gettext.bindtextdomain(APP, DIR)
        gettext.textdomain(APP)
        gtk.glade.bindtextdomain(APP, DIR)
        gtk.glade.textdomain(APP)

        # for the localisation of log file
        self.user = user

        # get glade tree
        self.gladefile = "../share/isodumper/isodumper.glade"
        self.wTree = gtk.glade.XML(self.gladefile)

        # get globally needed widgets
        self.window = self.wTree.get_widget("main_dialog")
        self.devicelist = self.wTree.get_widget("device_combobox")
        self.logview = self.wTree.get_widget("detail_text")
        self.log = self.logview.get_buffer()
        # set RELEASE number on title and About
        self.window.set_title(self.window.get_title()+' '+RELEASE)
        self.wTree.get_widget("about_dialog").set_version(RELEASE)

        # define size of the selected device
        self.deviceSize=0

        # Operation running
        self.operation=False

        # set default file filter to *.img
        # Added for Mageia : *.iso
        self.chooser = self.wTree.get_widget("filechooserbutton")
        filt = gtk.FileFilter()
        filt.add_pattern("*.iso")
        filt.add_pattern("*.img")
        self.chooser.set_filter(filt)


        # optionnal backup of the device
        self.backup_select = self.wTree.get_widget("backup_select")
        self.backup_name = self.wTree.get_widget("backup_name")
        self.backup_button = self.wTree.get_widget("backup_button")
        self.choose = self.wTree.get_widget("choose")
        self.backup_bname = self.wTree.get_widget("bname")


        # set callbacks
        dict = { "on_main_dialog_destroy_event" : self.confirm_close,
                 "on_main_dialog_delete_event" : self.confirm_close,
                 "on_cancel_button_clicked" : self.confirm_close,
                 "on_emergency_button_clicked" : self.restore,
                 "on_confirm_cancel_button_clicked": self.restore,
                 "on_filechooserbutton_file_set" : self.activate_devicelist,
                 "on_device_combobox_changed" : self.device_selected,
                 "on_nodev_close_clicked" : self.close,
                 "on_backup_button_clicked" : self.backup_go,
                 "on_backup_select_clicked" : self.backup_sel,
                 "on_select_clicked" : self.backup_choosed,
                 "on_about_button_clicked" : self.about,
                 "on_choose_cancel_clicked" : self.backup_cancel,
                 "on_format_button_clicked" : self.format_dialog,
                 "on_format_cancel_clicked" : self.format_cancel,
                 "on_format_go_clicked" : self.do_format,
                 "on_write_button_clicked" : self.do_write,
                 "on_help_close_clicked": self.help_close,
                 "on_help_clicked": self.help_dialog,
                 "on_update_button_clicked":self.update_list,
                 }
        self.wTree.signal_autoconnect(dict)

        self.window.show_all()
        # make sure we have a target device
        self.u = None
        try:
            self.u = UDisks2()
        except :
           self.logger(_('UDisks2 is not available on your system'))
           self.emergency()
        self.get_devices()

    def update_list(self, widget):
        self.devicelist.remove_text(0)
        self.get_devices()
        self.restore(widget)

    def get_devices(self):
        dialog = self.wTree.get_widget("nodev_dialog")
        self.list=self.u.find_devices()
        while len(self.list)==0:
            exit_dialog=dialog.run()
            if (exit_dialog==2) :
                dialog.destroy()
                exit(0)
            self.list = self.u.find_devices()
        for name, path, size in self.list:
                # convert in Mbytes
            sizeM=str(int(size)/(1024*1024))
            self.devicelist.append_text(name+' ('+path.lstrip()+') '+sizeM+_('Mb'))
        dialog.hide()

    def device_selected(self, widget):
        self.dev = self.devicelist.get_active_text()
        if self.dev != None:
            for name, path, size in self.list:
                if self.dev.startswith(name):
                    self.deviceSize=size
                    self.device_name=name.rstrip().replace(' ', '')
                    break
            self.backup_select.set_sensitive(True)
            self.wTree.get_widget("format_button").set_sensitive(True)
            self.chooser.set_sensitive(True)
            if self.chooser.get_current_folder_uri() == None :
                self.chooser.set_current_folder_uri('file:///home/'+self.user)
            self.logger(_('Target Device: ')+ self.dev)

    def backup_sel(self,widget):
        if self.backup_bname.get_current_folder_uri() == None :
            self.backup_bname.set_current_folder_uri('file:///home/'+self.user)
        self.backup_bname.set_current_name(self.device_name+".img")
        self.choose.run()

    def backup_cancel(self,widget):
        self.choose.hide()
           # Unckeck the choice to backup
        self.backup_button.set_sensitive(False)

    def backup_choosed(self, widget):
        exit_dialog=self.backup_bname.get_filename()
        if exit_dialog != None:
            # Add .iso if not specified
            if not exit_dialog.lower().endswith('.img'):
                exit_dialog=exit_dialog+".img"
            head, tail = os.path.split(exit_dialog)
            self.backup_dest=exit_dialog
            self.backup_select.set_label(tail)
            self.backup_button.set_sensitive(True)
            self.backup_select.set_tooltip_text(exit_dialog)
            self.logger(_('Backup in: ')+ exit_dialog)
            expander = self.wTree.get_widget("detail_expander")
            expander.set_sensitive(True)
        self.choose.hide()

    def format_dialog(self,widget):
        self.backup_select.set_sensitive(False)
        format_button=self.wTree.get_widget("format_button")
        format_button.set_sensitive(False)
        filechooserbutton=self.wTree.get_widget("filechooserbutton")
        filechooserbutton.set_sensitive(False)
        write_button = self.wTree.get_widget("write_button")
        write_button.set_sensitive(False)
        self.devicelist.set_sensitive(False)
        dialog=self.wTree.get_widget("format")
        self.wTree.get_widget("format_device").set_text(self.dev)
        self.wTree.get_widget("format_name").set_text(self.dev.split('(')[0])
        exit_dialog=dialog.run()
        if exit_dialog==0:
            dialog.hide()

    def do_format(self, widget)            :
        target = self.dev.split('(')[1].split(')')[0]
        dialog = self.wTree.get_widget("confirm_dialog")
        expander = self.wTree.get_widget("detail_expander")
        expander.set_sensitive(True)
        resp = dialog.run()
        dev_name=self.wTree.get_widget("format_name").get_text()
        if resp:
            dialog.hide()
            if self.wTree.get_widget("format_fat").get_active():
                rc=self.raw_format(target, 'fat32', dev_name.upper()[:11])
            if self.wTree.get_widget("format_ntfs").get_active():
                rc=self.raw_format(target, 'ntfs', dev_name[:32])
            if self.wTree.get_widget("format_ext4").get_active():
                rc=self.raw_format(target, 'ext4', dev_name)
            self.operation=False
            if rc == 0:
                message = _('The device was formatted successfully.')
                self.logger(message)
                self.success()
            elif rc == 5:
                message = _("An error occurred while creating a partition.")
                self.logger(message)
                self.emergency()
            elif rc == 127:
                message = _('Authentication error.')
                self.logger(message)
                self.emergency()
            else:
                message = _('An error occurred.')
                self.emergency()
            self.wTree.get_widget("format").hide()
            self.backup_select.set_sensitive(True)
            self.wTree.get_widget("format_button").set_sensitive(True)
            self.wTree.get_widget("filechooserbutton").set_sensitive(True)
        else:
            dialog.hide()

    def restore(self,widget):
        self.backup_select.set_sensitive(True)
        self.wTree.get_widget("format_button").set_sensitive(True)
        self.wTree.get_widget("filechooserbutton").set_sensitive(True)
        self.devicelist.set_sensitive(True)
        self.wTree.get_widget("emergency_dialog").hide()
        progress = self.wTree.get_widget("progressbar")
        progress.set_text("")
        progress.set_fraction(0)
        progress.set_sensitive(False)

    def raw_format(self, usb_path, fstype, label):
        self.operation=True
        if os.geteuid() > 0:
            launcher='pkexec'
            self.process = Popen([launcher,'/usr/bin/python', '-u', '/usr/lib/isodumper/raw_format.py','-d',usb_path,'-f',fstype, '-l', label, '-u', str(os.geteuid()), '-g', str(os.getgid())], shell=False, stdout=PIPE, preexec_fn=os.setsid)
        else:
            self.process = Popen(['/usr/bin/python', '-u', '/usr/lib/isodumper/raw_format.py','-d',usb_path,'-f',fstype, '-l', label, '-u', str(os.geteuid()), '-g', str(os.getgid())], shell=False, stdout=PIPE, preexec_fn=os.setsid)
        working=True
        while working:
            time.sleep(0.5)
            self.process.poll()
            rc=self.process.returncode
            if rc is None:
                working=True
            else:
                self.process = None
                working= False
        return rc

    def format_cancel(self, widget):
        dialog=self.wTree.get_widget("format")
        dialog.hide()
        self.backup_select.set_sensitive(True)
        format_button=self.wTree.get_widget("format_button")
        filechooserbutton=self.wTree.get_widget("filechooserbutton")
        format_button.set_sensitive(True)
        filechooserbutton.set_sensitive(True)
        self.devicelist.set_sensitive(True)

    def backup_go(self,widget):
        dest = self.backup_dest
        if os.path.exists(dest):
            dialog=self.wTree.get_widget("confirm_overwrite")
            resp=dialog.run()
            if resp !=-5: # GTK_RESPONSE_OK
                dialog.hide()
                return True
            else:
                dialog.hide()
        # check free space
        st = os.statvfs(os.path.dirname(dest))
        free = st.f_bavail * st.f_frsize
        if free<self.deviceSize :
            sizeM=str(self.deviceSize/(1024*1024))
            self.logger(_("The destination directory is too small to receive the backup (%s Mb needed)")%(sizeM))
            self.emergency()
        else:
            self.returncode=0
            source = self.dev.split('(')[1].split(')')[0]
            self.logger(_('Backup in:')+' '+dest)
            task = self.raw_write(source, dest, self.deviceSize)
            gobject.idle_add(task.next)
            while gtk.events_pending():
                gtk.main_iteration(True)
            if self.returncode==0:
            	self.success()

    def do_write(self, widget):
        write_button = self.wTree.get_widget("write_button")
        write_button.set_sensitive(False)
        combo = self.wTree.get_widget("device_combobox")
        combo.set_sensitive(False)
        format_button=self.wTree.get_widget("format_button")
        format_button.set_sensitive(False)
        backup_select=self.wTree.get_widget("backup_select")
        backup_select.set_sensitive(False)
        source = self.chooser.get_filename()
        target = self.dev.split('(')[1].split(')')[0]
        dialog = self.wTree.get_widget("confirm_dialog")
#        if self.backup.get_active() :
#            backup_dest=self.backup_select.get_label()
        self.logger(_('Image: ')+source)
        self.logger(_('Target Device: ')+self.dev)
        b = os.path.getsize(source)
        if b > (self.deviceSize):
            self.logger(_('The device is too small to contain the ISO file.'))
            self.emergency()
        else:
            resp = dialog.run()
            if resp:
                if self.deviceSize> 1024*1024*1024*32 :
                    message=self.wTree.get_widget("label1")
                    message.set_text(_('The device is bigger than 32 Gbytes. Are you sure you want use it?'))
                    resp = dialog.run()
                    if resp:
                        pass
                    else:
                        self.emergency()
                        dialog.hide()
                        return
                self.chooser.set_sensitive(False)
                self.do_umount(target)
                dialog.hide()
                # Writing step
                # Iso dump or Uefi preparation
                uefi_checkbox=self.wTree.get_widget("uefi_check")
                if uefi_checkbox.get_active():
                    #uefi mode : formats FAT32, names MGALIVE, copies the ISO
                    target = self.dev.split('(')[1].split(')')[0]
                    dev_name="MGALIVE"
                    rc=self.raw_format(target, 'fat32', dev_name)
                    if rc == 5:
                        message = _("An error occurred while creating a partition.")
                        self.logger(message)
                        self.emergency()
                    elif rc == 127:
                        message = _('Authentication error.')
                        self.logger(message)
                        self.emergency()
                    elif rc == 0:
                        message = _('The device was formatted successfully.')
                        self.logger(message)
#                        time.sleep(2)
                        seen=False
                        part=target+'1'
                        while(not seen):
                            try:
                                self.u.device(part)
                                seen=True
                            except:
                                seen=False
                                time.sleep(.5)
                        try:
                            dest=self.u.mount(part)
                        except:
                            self.logger(_("Error mounting the partition %s")%part)
                            self.emergency()
                            return
                        if dest!="":
                            self.logger(_("Mounted in: ")+dest)
                            self.returncode=0
                            task = self.files_write(source, dest)
                            gobject.idle_add(task.next)
                            self.operation=False
                            while gtk.events_pending():
                                gtk.main_iteration(True)
                            if self.returncode==0:
                                self.success()
                            else:
                                self.logger(_("Error copying files"))
                                self.emergency()
                        else:
                            self.operation=False
                            self.logger(_("Error mounting the partition %s")%part)
                            self.emergency()
                    else:
                        message = _('An error occurred.')
                        self.emergency()
                else:
                    #Dump mode
                    self.returncode=0
                    b=os.path.getsize(source)
                    task = self.raw_write(source, target, b)
                    gobject.idle_add(task.next)
                    while gtk.events_pending():
                        gtk.main_iteration(True)
                    task = self.check_write(target, b)
                    gobject.idle_add(task.next)
                    while gtk.events_pending():
                        gtk.main_iteration(True)
                    if self.returncode == 0:
                        self.success()
            else:
                dialog.hide()
                combo.set_sensitive(True)
                write_button.set_sensitive(True)
                format_button.set_sensitive(True)
                backup_select.set_sensitive(True)
    def do_umount(self, target):
        mounts = self.get_mounted(target)
        if mounts:
            self.logger(_('Unmounting all partitions of ')+target+':')
        for mount in mounts:
            self.logger(_('Trying to unmount ')+mount[0]+'...')
            while gtk.events_pending():
                gtk.main_iteration(True)
            try:
                retcode = call('umount '+mount[0], shell=True)
                if retcode < 0:
                    self.logger(_('Error, umount ')+mount[0]+_(' was terminated by signal ')+str(retcode))
                    self.emergency()
                else:
                    if retcode == 0:
                        self.logger(mount[0]+_(' successfully unmounted'))
                    else:
                        self.logger(_('Error, umount ')+mount[0]+_(' returned ')+str(retcode))
                        self.emergency()
            except OSError, e:
                self.logger(_('Execution failed: ')+str(e))
                self.emergency()

    def get_mounted(self, target):
        try:
            lines = [line.strip("\n").split(" ") for line in open ("/etc/mtab", "r").readlines()]
            return [mount for mount in lines if mount[0].startswith(target)]
        except:
             self.logger(_('Could not read mtab !'))
             self.emergency()

    def raw_write(self, source, target, b):
        self.operation=True
        
        bs=4096*128
        try:
            ifc=io.open(source, "rb",1)
        except:
             self.logger(_('Reading error.')+ source)
             self.emergency()
             return
        else:
            try:
                ofc= io.open(target, 'wb',0)
            except:
                 self.logger(_('You have not the rights for writing on the device'))
                 self.emergency()
                 self.close('dummy')
            else:
                progress = self.wTree.get_widget("progressbar")
                progress.set_sensitive(True)
                progress.set_text(_('Writing ')+source.split('/')[-1]+_(' to ')+target.split('/')[-1])
                self.logger(_('Executing copy from ')+source+_(' to ')+target)
                while gtk.events_pending():
                   gtk.main_iteration(True)
                steps=range(0, b+1, b/100)
                steps.append(b)
                indice=1
                written=0
                ncuts=b/bs
                while ncuts <= 100:
                    bs=bs/2
                    ncuts=b/bs
                for i in xrange(0,ncuts+1):
                    try:
                        buf=ifc.read(bs)
                    except:
                        self.logger(_("Reading error."))
                        self.emergency()
                        return
                    try:
                        ofc.write(buf)
                    except:
                        self.logger(_("Writing error."))
                        self.emergency()
                        return
                    written+=len(buf)
                    if written > steps[indice]:
                        if indice%1==0:
                            self.logger(_('Wrote: ')+str(indice)+'% '+str(written)+' bytes')
                            mark = self.log.create_mark("end", self.log.get_end_iter(), False)
                            self.logview.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)
                        progress.set_fraction(float(indice)/100)
                        indice +=1
                        try:
                            os.fsync(ofc)
                        except:
                           self.logger(_("Writing error."))
                           self.emergency()
                           return
                        yield True
                progress.set_fraction(1.0)
                self.logger(_('Image ')+source.split('/')[-1]+_(' successfully written to ')+target)
                self.logger(_('Bytes written: ')+str(written))
                try:
                    ofc.close()
                except:
                   self.logger(_("Writing error."))
                   self.emergency()
            ifc.close()
            yield False

    def check_write(self, target, b):
        import hashlib
        progress = self.wTree.get_widget("progressbar")
        progress.set_sensitive(True)
        progress.set_text(_('Checking ')+target.split('/')[-1])
        progress.set_fraction(0.0)
        steps=range(0, b+1, b/100)
        steps.append(b)
        indice=0
        checked=0
        sha1func=hashlib.sha1()
        md5func=hashlib.md5()
        ncuts=b/1024
        try:
    		with open(target, 'rb') as f:
    			for x in xrange(0,ncuts):
    				block = f.read(1024)
    				sha1func.update(block)
    				md5func.update(block)
    				if checked > steps[indice]:
    					progress.set_fraction(float(indice)/100)
    					indice +=1
    					while gtk.events_pending():
        					 gtk.main_iteration(True)
    					yield True
    				checked+=1024                         
    			block = f.read(b-ncuts*1024)
    			sha1func.update(block)
    			md5func.update(block)
    			sha1sumcalc=sha1func.hexdigest()
    			md5sumcalc=md5func.hexdigest()
    		self.logger(_('SHA1 sum: ')+sha1sumcalc)
    		self.logger(_('MD5  sum: ')+md5sumcalc)
    		mark = self.log.create_mark("end", self.log.get_end_iter(), False)
    		self.logview.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)
    		f.close()
    	except:
    		pass
        progress.set_fraction(1.0)
        yield False

    def files_write(self, source, dest):
        import shutil
        self.operation=True
        temp_dir='/mnt/MGALIVE'
        makedirs(temp_dir)
        self.process=Popen(['mount', '-o', 'loop',source,temp_dir ], shell=False, stdout=PIPE)
        working=True
        while working:
            time.sleep(0.5)
            self.process.poll()
            rc=self.process.returncode
            if rc is None:
                working=True
            else:
                self.process = None
                working=False
        self.logger(_('ISO image mounted in ')+temp_dir)
        progress = self.wTree.get_widget("progressbar")
        progress.set_sensitive(True)
        progress.set_text(_('Writing ')+source.split('/')[-1]+_(' to ')+dest)
        self.logger(_('Executing copy from ')+source+_(' to ')+dest)
        while gtk.events_pending():
           gtk.main_iteration(True)
        total_files=countFiles(temp_dir)
        self.logger(_("%s file(s) to copy."%total_files))
        if total_files > 0:
            numCopied = 0
            for path, dirs, filenames in os.walk(temp_dir):
                for directory in dirs:
                    destDir = path.replace(temp_dir,dest)
                    makedirs(os.path.join(destDir, directory))
                for sfile in filenames:
                    srcFile = os.path.join(path, sfile)
                    destFile = os.path.join(path.replace(temp_dir, dest), sfile)
                    shutil.copy2(srcFile, destFile)
                    numCopied += 1
                    progress.set_fraction(float(numCopied)/total_files)
                    yield True
            self.process = Popen(['umount', temp_dir ], shell=False, stdout=PIPE)
            self.logger(_('Image ')+source.split('/')[-1]+_(' successfully written to ')+dest)
        else:
            self.returncode=1

    def success(self):
        self.operation=False
        dialog = self.wTree.get_widget("success_dialog")
        self.final_unsensitive()
        resp = dialog.run()
        if resp:
#            exit(0)
            dialog.hide()


    def confirm_close(self, widget, *args):
        if self.operation==False:    # no writing , backup nor format running
            self.close('dummy')
        else:   # writing , backup or format running
            dialog=self.wTree.get_widget("Quit_warning")
            resp = dialog.run()
            if resp==-5 :   # GTK_RESPONSE_OK
               self.close('dummy')
            else:
                dialog.hide()
                return True

    def emergency(self):
        self.operation=False
        self.returncode=1
        self.final_unsensitive()
        dialog = self.wTree.get_widget("emergency_dialog")
        expander = self.wTree.get_widget("detail_expander")
        expander.set_expanded(True)
        mark = self.log.create_mark("end", self.log.get_end_iter(), False)
        self.logview.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)
        resp = dialog.run()
        if resp:
            dialog.hide()
#            self.close()

    def final_unsensitive(self):
        self.chooser.set_sensitive(False)
        self.devicelist.set_sensitive(False)
        write_button = self.wTree.get_widget("write_button")
        write_button.set_sensitive(False)
        progress = self.wTree.get_widget("progressbar")
        progress.set_sensitive(False)
        self.backup_select.set_sensitive(False)

    def close(self, widget):
        self.write_logfile()
        gtk.main_quit()
        exit(0)

    def write_logfile(self):
        start = self.log.get_start_iter()
        end = self.log.get_end_iter()
        import pwd
        pw = pwd.getpwnam(self.user)
        uid = pw.pw_uid
        gid=pw.pw_gid
        if (self.user != 'root') and (self.user !=''):
            logpath='/home/'+self.user+'/.isodumper'
            os.setgid(gid)
            os.setuid(uid)
            if not(os.path.isdir(logpath)):
                os.mkdir(logpath)
        else:
            logpath='/root'
        logfile=open(logpath+'/isodumper.log',"w")
        logfile.write(self.log.get_text(start, end, False))
        logfile.close()

        print self.log.get_text(start, end, False)

    def logger(self, text):
        self.log.insert_at_cursor(text+"\n")

    def activate_devicelist(self, widget):
#        label = self.wTree.get_widget("to_label")
        expander = self.wTree.get_widget("detail_expander")
#        self.devicelist.set_sensitive(True)
        expander.set_sensitive(True)
#        label.set_sensitive(True)
        self.img_name = self.chooser.get_filename()
        write_button = self.wTree.get_widget("write_button")
        write_button.set_sensitive(True)
        self.logger(_('Image ')+": "+ self.img_name)
        self.chooser.set_tooltip_text(self.img_name)

    def activate_backup(self, widget):
        self.backup_img_name = self.backup_dir.get_filename()

#    def expander_control(self, widget):
#        # this is darn ugly but still better than the UI behavior of
#        # the unexpanded expander which doesnt reset the window size
#        if widget.get_expanded():
#            gobject.timeout_add(130, lambda: self.window.reshow_with_initial_size())

    def help_dialog(self, widget):
        dialog = self.wTree.get_widget("help_dialog")
        dialog.run()

    def help_close(self, widget):
        dialog = self.wTree.get_widget("help_dialog")
        dialog.hide()

    def about(self, widget):
        about_button = self.wTree.get_widget("about_button")
        about_button.set_sensitive(True)
        dialog = self.wTree.get_widget("about_dialog")
        resp = dialog.run()
        if resp:
            dialog.hide()

if __name__ == "__main__":
    import sys
    user=sys.argv[1]
    app = IsoDumper(user)
    gtk.main()
