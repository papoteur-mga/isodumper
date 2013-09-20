#!/usr/bin/python
#  
#  Copyright (c) 2007-2009 Canonical Ltd.
#  
#  Author: Oliver Grawert <ogra@ubuntu.com>
# 
#  Modifications 2013 from papoteur <papoteur@mageialinux-online.org>
#  and Geiger David <david.david@mageialinux-online.org>
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
from subprocess import Popen,PIPE,call
import os
import signal

import gettext
from gettext import gettext as _


class ImageWriter:
    def __init__(self):
        APP="isodumper"
        DIR="/usr/share/locale"

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
        #eventbox = self.wTree.get_widget("eventbox")
        #bgcol = gtk.gdk.color_parse("white")
        #eventbox.modify_bg(gtk.STATE_NORMAL, bgcol)
        self.log = self.logview.get_buffer()
        self.ddpid = 0

        # set default file filter to *.img
        # Added for Mageia : *.iso
        self.chooser = self.wTree.get_widget("filechooserbutton")
        filt = gtk.FileFilter()
        filt.add_pattern("*.iso")
        filt.add_pattern("*.img")
        self.chooser.set_filter(filt)

        # set callbacks
        dict = { "on_main_dialog_destroy" : self.close,
                 "on_cancel_button_clicked" : self.close,
                 "on_emergency_button_clicked" : self.close,
                 "on_success_button_clicked" : self.close,
                 "on_filechooserbutton_file_set" : self.activate_devicelist,
                 "on_detail_expander_activate" : self.expander_control,
                 "on_device_combobox_changed" : self.device_selected,
                 "on_button1_clicked" : self.close,
                 "on_write_button_clicked" : self.do_write}
        self.wTree.signal_autoconnect(dict)

        self.window.show_all()
        # make sure we have a target device
        self.get_devices()

    def get_devices(self):
        dialog = self.wTree.get_widget("nodev_dialog")
        list = Popen(["/usr/lib/isodumper/find_devices"], stdout=PIPE).communicate()[0]
        if not len(list):
            dialog.run()
        list = Popen(["/usr/lib/isodumper/find_devices"], stdout=PIPE).communicate()[0]
        if not len(list):
            dialog.destroy()
            self.close
            exit(0)
        self.combo = self.wTree.get_widget("device_combobox")
        list = list.strip().split('\n')
        for item in list:
            name,path = item.split(',')
            self.combo.append_text(name+' ('+path.lstrip()+')')
        dialog.destroy()

    def device_selected(self, widget):
        write_button = self.wTree.get_widget("write_button")
        write_button.set_sensitive(True)
        self.dev = self.combo.get_active_text()

    def do_write(self, widget):
        write_button = self.wTree.get_widget("write_button")
        write_button.set_sensitive(False)
        combo = self.wTree.get_widget("device_combobox")
        combo.set_sensitive(False)
        self.chooser.set_sensitive(False)
        source = self.chooser.get_filename()
        target = self.dev.split('(')[1].rstrip(')')
        dialog = self.wTree.get_widget("confirm_dialog")
        self.logger(_('Image: ')+source)
        self.logger(_('Target Device: ')+self.dev)
        resp = dialog.run()
        if resp:
            self.do_umount(target)
            dialog.hide()
            task = self.raw_write(source, target)
            gobject.idle_add(task.next)
            while gtk.events_pending():
                gtk.main_iteration(True)
            
        else:
            self.close('dummy')

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

    def raw_write(self, source, target):
        bs=4096*128
        b = os.path.getsize(source)
        try:
            ifc=open(source, "rb",1)
        except:
             self.logger(_('Reading error.'))
             self.emergency()
        else:
            try:
                ofc= open(target, 'wb',0)
            except:
                 self.logger(_('You have not the rights for writing on the device'))
                 self.emergency()
            else:
                progress = self.wTree.get_widget("progressbar")
                progress.set_sensitive(True)
                progress.set_text(_('Writing ')+source.split('/')[-1]+_(' to ')+self.dev)
                self.logger(_('Executing copy from ')+source+' to '+target)
                while gtk.events_pending():
                   gtk.main_iteration(True)
                steps=range(0, b+1, b/100)
                indice=1
                written=0
                ncuts=b/bs
                for i in xrange(0,ncuts):
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
                    written= written+bs
                    if written > steps[indice]:
                        if indice%1==0:
                            self.logger(_('Wrote: ')+str(indice)+'% '+str(written)+' bytes')
                            mark = self.log.create_mark("end", self.log.get_end_iter(), False)
                            self.logview.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)
                        progress.set_fraction(float(indice)/100)
                        indice +=1
                        os.fsync(ofc)
                        yield True
                progress.set_fraction(1.0)
                self.logger(_('Image ')+source.split('/')[-1]+_(' successfully written to')+target)
                self.logger(_('Bytes written: ')+str(written))
                ofc.close()
                self.success()
            ifc.close()
            yield False

    def success(self):
        dialog = self.wTree.get_widget("success_dialog")
        self.final_unsensitive()
        resp = dialog.run()
        if resp:
            exit(0)
            dialog.destroy()

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

    def final_unsensitive(self):
        self.chooser.set_sensitive(False)
        self.devicelist.set_sensitive(False)
        write_button = self.wTree.get_widget("write_button")
        write_button.set_sensitive(False)
        progress = self.wTree.get_widget("progressbar")
        progress.set_sensitive(False)

    def close(self, widget):
        self.write_logfile()
        if self.ddpid > 0:
            try:
                os.killpg(os.getpgid(self.ddpid), signal.SIGKILL)
            except:
                gtk.main_quit()
        else:
            gtk.main_quit()

    def write_logfile(self):
        start = self.log.get_start_iter()
        end = self.log.get_end_iter()
        from os.path import expanduser
        home = expanduser("~")
        if not(os.path.isdir(home+'/.isodumper')):
            os.mkdir(home+'/.isodumper')
        logfile=open(home+'/.isodumper/isodumper.log',"w")
        logfile.write(self.log.get_text(start, end, False))
        print self.log.get_text(start, end, False)

    def logger(self, text):
        self.log.insert_at_cursor(text+"\n")

    def activate_devicelist(self, widget):
        label = self.wTree.get_widget("to_label")
        expander = self.wTree.get_widget("detail_expander")
        self.devicelist.set_sensitive(True)
        expander.set_sensitive(True)
        label.set_sensitive(True)
        self.img_name = self.chooser.get_filename()

    def expander_control(self, widget):
        # this is darn ugly but still better than the UI behavior of
        # the unexpanded expander which doesnt reset the window size
        if widget.get_expanded():
            gobject.timeout_add(130, lambda: self.window.reshow_with_initial_size())

if __name__ == "__main__":
    app = ImageWriter()
    gtk.main()
