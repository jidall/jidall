#define MyAppName "Assistente de Provas"
#define MyAppVersion "1.0.1"
[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename=Assistente_de_Provas_Setup
Compression=lzma
SolidCompression=yes
UninstallDisplayIcon={app}\Assistente de Provas.exe
[Files]
Source: "..\dist\Assistente de Provas\*"; DestDir: "{app}"; Flags: recursesubdirs
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Assistente de Provas.exe"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\Assistente de Provas.exe"
[Run]
Filename: "{app}\Assistente de Provas.exe"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
