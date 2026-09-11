Name:           nexo-solar
Version:        %{?nexo_version}%{!?nexo_version:1.0.0}
Release:        1%{?dist}
Summary:        Nexo Solar desktop application for Davis WeatherLink monitoring
License:        Proprietary
URL:            https://github.com/EdinsonMoreno/nexo-solar
BuildArch:      x86_64

%description
Nexo Solar is a desktop application for solar and meteorological monitoring
with Davis WeatherLink acquisition, SQLite storage, and a PyQt6 web dashboard.

%prep

%build

%install
rm -rf %{buildroot}
mkdir -p "%{buildroot}/opt/nexo-solar"
cp -a "%{project_root}/dist/Nexo Solar/." "%{buildroot}/opt/nexo-solar/"

mkdir -p "%{buildroot}/usr/bin"
cat > "%{buildroot}/usr/bin/nexo-solar" <<'EOF'
#!/usr/bin/env bash
exec "/opt/nexo-solar/Nexo Solar" "$@"
EOF
chmod 0755 "%{buildroot}/usr/bin/nexo-solar"

mkdir -p "%{buildroot}/usr/share/applications"
install -m 0644 "%{project_root}/packaging/fedora/nexo-solar.desktop" "%{buildroot}/usr/share/applications/nexo-solar.desktop"

mkdir -p "%{buildroot}/usr/share/pixmaps"
install -m 0644 "%{project_root}/modbuspython/assets/LogoNexoSolar.png" "%{buildroot}/usr/share/pixmaps/nexo-solar.png"

%files
/opt/nexo-solar
/usr/bin/nexo-solar
/usr/share/applications/nexo-solar.desktop
/usr/share/pixmaps/nexo-solar.png

%changelog
* Fri Sep 11 2026 Edinson Andres Moreno Cepeda <edinson@example.com> - 1.0.0-1
- Stable Fedora package for Nexo Solar.
