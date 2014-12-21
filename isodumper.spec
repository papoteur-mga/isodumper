Name:		isodumper
Version:	0.40
Release:	%mkrel 1
Summary:	Tool for writing ISO images on a USB stick
Summary(fr_FR):	Outil pour écrire des images ISO sur une clé USB
License:	GPLv2+ and LGPLv2+
Group:		System/Configuration
URL:		https://github.com/papoteur-mga/isodumper
# wget https://github.com/papoteur-mga/isodumper/archive/%%{version}.tar.gz -O %%{name}-%%{version}.tar.gz
Source0:	%{name}-%{version}.tar.gz
BuildArch:	noarch

BuildRequires:	imagemagick
BuildRequires:	intltool

Requires:	coreutils
Requires:	pango
Requires:	polkit
Requires:	procps-ng
Requires:	pygtk2.0-libglade
Requires:	python
Requires:	python-dbus
Requires:	python-parted
Requires:	udisks
Requires:	xterm


%description
A GUI tool for writing ISO images on a USB stick.
It's a fork of usb-imagewriter.

This software is written in python.

%description -l fr_FR
Un outil graphique pour écrire des images ISO sur une clé USB.
C'est un fork de usb-imagewriter

Ce logiciel est écrit en python.

#--------------------------------------------------------------------
%prep
%setup -q

%build
%make

%install
%makeinstall_std

%find_lang %{name}

%files -f %{name}.lang
%doc COPYING.* CHANGELOG
%{_bindir}/%{name}
%{_libexecdir}/%{name}
%{_usr}/lib/%{name}/
%{_datadir}/%{name}/
%{_datadir}/polkit-1/actions/*.policy
%{_datadir}/applications/%{name}.desktop
%{_datadir}/pixmaps/%{name}.png
%{_miconsdir}/%{name}.png
%{_iconsdir}/%{name}.png
%{_liconsdir}/%{name}.png
%{_iconsdir}/hicolor/*/*/%{name}.png
%{_iconsdir}/hicolor/*/*/%{name}.svg
