# -*- coding: utf-8 -*-
"""
Created on Tue Jun 25 19:00:13 2013

@author: yves
"""
import os
# Block size
    def raw_write(self, source, target):
        bs=4096
        b = os.path.getsize("/documents/boot-nonfree.iso")
        ifc=open(source, "rb",1)
        ofc= open("/documents/test.iso", 'wb',0)
        progress = self.wTree.get_widget("progressbar")
        progress.set_sensitive(True)
        progress.set_text(_('Writing ')+source.split('/')[-1]+_(' to ')+self.dev)
        self.logger(_('Executing copy from ')+source+' to '+target)
        while gtk.events_pending():
           gtk.main_iteration(True)
        #output = Popen(['dd if='+source+' of='+target+' bs=1024'], stdout=PIPE, stderr=STDOUT, shell=True)
        #self.ddpid = output.pid
        #while output.stdout.readline():
        #    line = output.stdout.readline().strip()
        steps=range(0, b, b/100)
        indice=1
        written=0
        for i in xrange(0,b,bs):
            try:
                buf=ifc.read(bs)
            except:
                self.logger(_("Reading error."))
                return False
            try:
                ofc.write(buf)
            except:
                self.logger(_("Writing error."))
                return False
            written= written+bs
            if written > steps[indice]:
                indice +=1
                while gtk.events_pending():
                    gtk.main_iteration(True)
            #if line.endswith('MB/s'):
            #    target_size = line.split()[0]
                self.logger(_('Wrote: ')+written+' bytes')
                #size = float(target_size)*100/float(src_size)
                while gtk.events_pending():
                    gtk.main_iteration(True)
                progress.set_fraction(float(indice/100))
        #pid, sts = os.waitpid(output.pid, 0)
        #if sts != 0:
        #    self.logger(_('The dd process ended with an error !'))
        #    self.emergency()
        #    return False
        progress.set_fraction(1.0)
        self.logger(_('Image ')+source.split('/')[-1]+_(' successfully written to')+target)
        self.logger(_("%s octets écrits")%written)
        self.success()

        # tous les 5%
            
        ifc.close()
        ofc.close()
        print 
