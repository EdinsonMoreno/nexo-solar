; Script de Inno Setup para Nexo Solar
; Generado para instalar la aplicación y sus dependencias

[Setup]
AppName=Nexo Solar
AppVersion=1.0
DefaultDirName={pf}\NexoSolar
DefaultGroupName=Nexo Solar
UninstallDisplayIcon={app}\Nexo Solar.exe
OutputDir=.
OutputBaseFilename=Nexo Solar_Installer
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; Ejecutable principal
Source: "dist\Nexo Solar\Nexo Solar.exe"; DestDir: "{app}"; Flags: ignoreversion
; Todo el contenido de la app (recursos, módulos, datos, etc.)
Source: "dist\Nexo Solar\_internal\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Nexo Solar"; Filename: "{app}\Nexo Solar.exe"
Name: "{group}\Desinstalar Nexo Solar"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\Nexo Solar.exe"; Description: "Iniciar Nexo Solar"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\assets"
Type: filesandordirs; Name: "{app}\BannerISS"
Type: filesandordirs; Name: "{app}\ico"
Type: filesandordirs; Name: "{app}\ui"
Type: filesandordirs; Name: "{app}\backend"

; Fin del script
