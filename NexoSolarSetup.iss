; Script de Inno Setup para Nexo Solar
; Generado para instalar la aplicación y sus dependencias

#ifndef NexoSolarVersion
#define NexoSolarVersion "1.0.0"
#endif

[Setup]
AppName=Nexo Solar
AppVersion={#NexoSolarVersion}
DefaultDirName={pf}\NexoSolar
DefaultGroupName=Nexo Solar
UninstallDisplayIcon={app}\Nexo Solar.exe
OutputDir=dist\installers\windows
OutputBaseFilename=NexoSolar-Setup-Windows-x64
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; Todo el contenido generado por PyInstaller
Source: "dist\Nexo Solar\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

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
