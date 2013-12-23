# Copyright (C) 2013 THE isodumper'S COPYRIGHT HOLDER
# This file is distributed under the same license as the isodumper package.

# This Makefile is free software; the Free Software Foundation
# gives unlimited permission to copy and/or distribute it,
# with or without modifications, as long as this notice is preserved.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY, to the extent permitted by law; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.

# Author isodumper software= papoteur <papoteur@mageialinux-online.org>
# Author Makefile file= Yuri Chornoivan <yurchor@ukr.net>

BINDIR = /usr/bin
LIBEXECDIR = /usr/libexec
BINDEST = $(DESTDIR)$(BINDIR)
POLKITPOLICYDEST = $(DESTDIR)/usr/share/polkit-1/actions

POLICY_IN := $(wildcard *.policy.in)
POLICY = $(POLICY_IN:.policy.in=.policy)
WRAPPERS = $(patsubst org.mageia.%.policy,%,$(POLICY))

all: $(WRAPPERS) $(POLICY)

clean:
	rm -f  $(WRAPPERS) $(POLICY)

%: org.mageia.%.policy.in
	@echo -e '#!/bin/sh\nif  [[ "$$UID" != "0" ]] ; then\n    exec $(BINDIR)/pkexec $(LIBEXECDIR)/$@ "$$''@"\nelse\n    exec $(LIBEXECDIR)/$@ "$$''@"\nfi\n' > $@

%.policy: %.policy.in
	intltool-merge --utf8 ../po $< $@ -x -u -c ../po/.intltool-merge-cache

install: all
	install -d $(BINDEST) $(POLKITPOLICYDEST)
	install -m755 $(WRAPPERS) $(BINDEST)
	install -m644 $(POLICY) $(POLKITPOLICYDEST)
