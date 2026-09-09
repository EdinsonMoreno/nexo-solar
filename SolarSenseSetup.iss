; Script de Inno Setup para SolarSense SCADA
; Generado para instalar la aplicación y sus dependencias

[Setup]
AppName=SolarSense SCADA
AppVersion=1.0
DefaultDirName={pf}\SolarSenseSCADA
DefaultGroupName=SolarSense SCADA
UninstallDisplayIcon={app}\SolarSense.exe
OutputDir=.
OutputBaseFilename=SolarSense_Installer
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; Ejecutable principal
Source: "dist\SolarSense\SolarSense.exe"; DestDir: "{app}"; Flags: ignoreversion
; Todo el contenido de la app (recursos, módulos, datos, etc.)
Source: "dist\SolarSense\_internal\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SolarSense SCADA"; Filename: "{app}\SolarSense.exe"
Name: "{group}\Desinstalar SolarSense SCADA"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\SolarSense.exe"; Description: "Iniciar SolarSense SCADA"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\assets"
Type: filesandordirs; Name: "{app}\BannerISS"
Type: filesandordirs; Name: "{app}\ico"
Type: filesandordirs; Name: "{app}\ui"
Type: filesandordirs; Name: "{app}\backend"

; Fin del script
