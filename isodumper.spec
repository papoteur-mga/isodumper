Name:		isodumper
Version:	0.10
Release:	%mkrel 1
Summary:	Tool for writing ISO images on a USB stick
Summary(fr_FR):	Outil pour écrire des images ISO sur une clé USB
License:	GPLv2+
Group:		System/Configuration
URL:		https://github.com/papoteur-mga/isodumper
# wget https://github.com/papoteur-mga/isodumper/archive/%%{version}.tar.gz -O %%{name}-%%{version}.tar.gz
Source0:	%{name}-%{version}.tar.gz
BuildArch:	noarch

BuildRequires:	imagemagick
BuildRequires:	usermode-consoleonly

Requires:	coreutils
Requires:	udisks
Requires:	procps
Requires:	python
Requires:	xterm
Requires:	pygtk2.0-libglade

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
%setup_compile_flags

%install
mkdir -p %{buildroot}%{_sbindir}
mkdir -p %{buildroot}%{_usr}/lib/%{name}
mkdir -p %{buildroot}%{_datadir}/%{name}

install -m 755 isodumper %{buildroot}%{_sbindir}/%{name}
install -m 644 share/%{name}/%{name}.glade %{buildroot}%{_datadir}/%{name}/%{name}.glade
install -m 644 share/%{name}/header.png %{buildroot}%{_datadir}/%{name}/header.png

# desktop menu entry
mkdir -p %{buildroot}%{_datadir}/applications
install -m 644 share/applications/%{name}.desktop %{buildroot}%{_datadir}/applications/%{name}.desktop

# LIBFILES isodumper.py find_devices
install -m 755 lib/find_devices %{buildroot}%{_usr}/lib/%{name}/find_devices
install -m 755 lib/%{name}.py %{buildroot}%{_usr}/lib/%{name}/%{name}.py

# isodumper.mo translations
pushd share/locale
for f in *;
do
		poname=${f:0:5}
		mkdir -p %{buildroot}%{_datadir}/locale/$poname/LC_MESSAGES
		install -m 644 $poname/LC_MESSAGES/%{name}.mo \
		"%{buildroot}%{_datadir}/locale/$poname/LC_MESSAGES/"
done
popd

# icons
mkdir -p %{buildroot}/{%{_liconsdir},%{_miconsdir},%{_iconsdir}}
convert %{name}.png -geometry 20x20 %{buildroot}/%{_miconsdir}/%{name}.png
convert %{name}.png -geometry 32x32 %{buildroot}/%{_iconsdir}/%{name}.png
convert %{name}.png -geometry 48x48 %{buildroot}/%{_liconsdir}/%{name}.png

# Adjust for console-helper magic
mkdir -p %{buildroot}%{_bindir}
pushd %{buildroot}%{_bindir}
ln -s consolehelper %{name}
popd

%find_lang %{name}

%files -f %{name}.lang
%doc COPYING CHANGELOG
%{_sbindir}/%{name}
%{_bindir}/%{name}
%{_usr}/lib/%{name}/
%{_datadir}/%{name}/
%{_datadir}/applications/%{name}.desktop
%{_miconsdir}/%{name}.png
%{_iconsdir}/%{name}.png
%{_liconsdir}/%{name}.png

