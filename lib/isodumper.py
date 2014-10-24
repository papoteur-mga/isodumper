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

import gtk
import gtk.glade
import gobject
import os
import io
import gettext
from gettext import gettext as _
from subprocess import call

def find_devices():
    import dbus
    bus = dbus.SystemBus()
    proxy = bus.get_object("org.freedesktop.UDisks", "/org/freedesktop/UDisks")
    iface = dbus.Interface(proxy, "org.freedesktop.UDisks")
    devs=iface.EnumerateDevices()
    list=[]

    for dev in devs:
    	dev_obj = bus.get_object("org.freedesktop.UDisks", dev)
    	dev = dbus.Interface(dev_obj, "org.freedesktop.DBus.Properties")
    	item=[]
    	if str(dev.Get('', 'DriveConnectionInterface')) == 'usb' and not str(dev.Get('', 'PartitionType')) and str(dev.Get('', 'DeviceIsMediaAvailable')) == '1':
		vend = str(dev.Get('', 'DriveVendor'))
    		path = str(dev.Get('', 'DeviceFile'))
     		name = str(dev.Get('', 'DriveModel'))
    		size = str(dev.Get('', 'DeviceSize'))
    		item.append(vend+" "+name)
    		item.append(path)
    		item.append(size)
    		list.append(item)
    print list
    return list


class IsoDumper:
    def __init__(self):
        APP="isodumper"
        DIR="/usr/share/locale"
        RELEASE="v0.23"
        # for the localisation of log file

        gettext.bindtextdomain(APP, DIR)
        gettext.textdomain(APP)
        gtk.glade.bindtextdomain(APP, DIR)
        gtk.glade.textdomain(APP)

        # get glade tree
        self.gladefile = "/usr/share/isodumper/isodumper.glade"
        self.wTree = gtk.glade.XML(self.gladefile)

        # get globally needed widgets
        self.window = self.wTree.get_widget("main_dialog")
        self.devicelist = self.wTree.get_widget("device_combobox")
        self.logview = self.wTree.get_widget("detail_text")
        self.log = self.logview.get_buffer()

        self.window.set_title(self.window.get_title()+' '+RELEASE)
        self.wTree.get_widget("about_dialog").set_version(RELEASE)

        # define size of the selected device
        self.deviceSize=0

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
        self.backup = self.wTree.get_widget("backup")
        self.choose = self.wTree.get_widget("choose")
        self.backup_bname = self.wTree.get_widget("bname")


        # set callbacks
        dict = { "on_main_dialog_destroy" : self.close,
                 "on_cancel_button_clicked" : self.close,
                 "on_emergency_button_clicked" : self.close,
                 "on_filechooserbutton_file_set" : self.activate_devicelist,
                 "on_backup_name_file_set" : self.activate_backup,
#                 "on_detail_expander_activate" : self.expander_control,
                 "on_device_combobox_changed" : self.device_selected,
                 "on_nodev_close_clicked" : self.close,
                 "on_backup_toggled" : self.enable_backup,
                 "on_backup_select_clicked" : self.backup_sel,
                 "on_select_clicked" : self.backup_choosed,
                 "on_choose_cancel_clicked" : self.backup_cancel,
                 "on_about_button_clicked" : self.about,
                 "on_write_button_clicked" : self.do_write,
                 "on_main_dialog_delete_event" : gtk.main_quit,}
        self.wTree.signal_autoconnect(dict)


        self.window.show_all()
        # make sure we have a target device
        self.get_devices()


    def get_devices(self):
        dialog = self.wTree.get_widget("nodev_dialog")
        list=find_devices()
        while len(list)==0:
            exit_dialog=dialog.run()
            list = find_devices()
            if (exit_dialog==2) :
                dialog.destroy()
                exit(0)
        self.combo = self.wTree.get_widget("device_combobox")
        for name, path, size in list:
            self.deviceSize=size
                # convert in Mbytes
            sizeM=str(int(size)/(1024*1024))
            self.combo.append_text(name+' ('+path.lstrip()+') '+sizeM+_('Mb'))
            self.device_name=name.rstrip().replace(' ', '')
        dialog.destroy()


    def device_selected(self, widget):
        write_button = self.wTree.get_widget("write_button")
        write_button.set_sensitive(True)
        self.dev = self.combo.get_active_text()
        self.logger(_('Target Device: ')+ self.dev)

    def enable_backup(self,widget) :
        self.backup_select.set_sensitive(not self.backup_select.get_sensitive())

    def backup_sel(self,widget):
        if (self.backup_bname.get_current_folder_uri() == None)  :
            self.backup_bname.set_current_folder_uri('file:///home/'+os.getlogin())
        self.backup_bname.set_current_name(self.device_name+".img")
        self.choose.run()

    def backup_cancel(self,widget):
        self.choose.hide()
           # Unckeck the choice to backup
        self.backup.set_active(0)

    def backup_choosed(self, widget):
        exit_dialog=self.backup_bname.get_filename()
        if exit_dialog == None:
            # No backup file name indicated
            # Unckeck the choice to backup
            self.backup.set_active(0)
        else:
            # Add .img if not specified
            if not exit_dialog.lower().endswith('.img'):
                exit_dialog=exit_dialog+".img"
            self.backup_select.set_label(exit_dialog)
        self.choose.hide()

    def do_write(self, widget):
        write_button = self.wTree.get_widget("write_button")
        write_button.set_sensitive(False)
        combo = self.wTree.get_widget("device_combobox")
        combo.set_sensitive(False)
        source = self.chooser.get_filename()
        target = self.dev.split('(')[1].split(')')[0]
        dialog = self.wTree.get_widget("confirm_dialog")
        if self.backup.get_active() :
            backup_dest=self.backup_select.get_label()
            self.logger(_('Backup in:')+' '+backup_dest)
        self.logger(_('Image: ')+source)
        self.logger(_('Target Device: ')+self.dev)
        b = os.path.getsize(source)
        if b > (eval(self.deviceSize)) :
            self.logger(_('The device is too small to contain the ISO file.'))
            self.emergency()
        else:
            resp = dialog.run()
            if resp:
                if eval(self.deviceSize)> 1024*1024*1024*32 :
                    message=self.wTree.get_widget("label1")
                    message.set_text(_('The device is bigger than 32 Gbytes. Are you sure you want use it?'))
                    resp = dialog.run()
                    if resp:
                        pass
                    else:
#                        self.close('dummy')
                        self.emergency()
                        dialog.hide()
                self.backup_select.set_sensitive(False)
                self.backup.set_sensitive(False)
                self.chooser.set_sensitive(False)
                self.do_umount(target)
                dialog.hide()
                # Backup step
                if self.backup.get_active() :
                    task = self.raw_write(target, backup_dest, eval(self.deviceSize))
                    gobject.idle_add(task.next)
                    while gtk.events_pending():
                        gtk.main_iteration(True)
                # Writing step
                task = self.raw_write(source, target, os.path.getsize(source))
                gobject.idle_add(task.next)
                while gtk.events_pending():
                    gtk.main_iteration(True)
                self.success()
            else:
#                self.close('dummy')
                dialog.hide()
                combo.set_sensitive(True)
                write_button.set_sensitive(True)
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
        bs=4096*128
        try:
            ifc=io.open(source, "rb",1)
        except:
             self.logger(_('Reading error.'))
             self.emergency()
        else:
            try:
                ofc= io.open(target, 'wb',0)
            except:
                 self.logger(_('You have not the rights for writing on the device'))
                 self.emergency()
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
                    try:
                        ofc.write(buf)
                    except:
                        self.logger(_("Writing error."))
                        self.emergency()
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

    def success(self):
        dialog = self.wTree.get_widget("success_dialog")
        self.final_unsensitive()
        resp = dialog.run()
        if resp:
#            exit(0)
            dialog.hide()


    def emergency(self):
        self.final_unsensitive()
        dialog = self.wTree.get_widget("emergency_dialog")
        expander = self.wTree.get_widget("detail_expander")
        expander.set_expanded(True)
        mark = self.log.create_mark("end", self.log.get_end_iter(), False)
        self.logview.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)
        resp = dialog.run()
        if resp:
            dialog.destroy()
            self.close()

    def final_unsensitive(self):
        self.chooser.set_sensitive(False)
        self.devicelist.set_sensitive(False)
        write_button = self.wTree.get_widget("write_button")
        write_button.set_sensitive(False)
        progress = self.wTree.get_widget("progressbar")
        progress.set_sensitive(False)

    def close(self, widget):
        self.write_logfile()
        gtk.main_quit()
        exit(0)

    def write_logfile(self):
        start = self.log.get_start_iter()
        end = self.log.get_end_iter()
        user = os.getlogin()
        import pwd
        pw = pwd.getpwnam(user)
        uid = pw.pw_uid
        gid=pw.pw_gid
        if (user != 'root') and (user !=''):
            logpath='/home/'+user+'/.isodumper'
            os.setgid(gid)
            os.setuid(uid)
            if not(os.path.isdir(logpath)):
                os.mkdir(logpath)
        else:
            logpath='/root'
        logfile=open(logpath+'/isodumper.log',"w")
        logfile.write(self.log.get_text(start, end, False))
        logfile.close()

    def logger(self, text):
        self.log.insert_at_cursor(text+"\n")

    def activate_devicelist(self, widget):
        label = self.wTree.get_widget("to_label")
        expander = self.wTree.get_widget("detail_expander")
        self.devicelist.set_sensitive(True)
        expander.set_sensitive(True)
        label.set_sensitive(True)
        self.img_name = self.chooser.get_filename()
        self.logger(_('Image ')+": "+ self.img_name)
        self.chooser.set_tooltip_text(self.img_name)


    def activate_backup(self, widget):
        self.backup_img_name = self.backup_dir.get_filename()

#    def expander_control(self, widget):
#        # this is darn ugly but still better than the UI behavior of
#        # the unexpanded expander which doesnt reset the window size
#        if widget.get_expanded():
#            #gobject.timeout_add(130, lambda: self.window.reshow_with_initial_size())
#            pass

    def about(self, widget):
        about_button = self.wTree.get_widget("about_button")
        about_button.set_sensitive(True)
        dialog = self.wTree.get_widget("about_dialog")
        resp = dialog.run()
        if resp:
            dialog.hide()
            #exit(0)

if __name__ == "__main__":
    app = IsoDumper()
    gtk.main()
