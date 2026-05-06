[Setup]
AppName=Grammar Tool
AppVersion=1.0
DefaultDirName={autopf}\GrammarTool
DefaultGroupName=Grammar Tool
UninstallDisplayIcon={app}\GrammarTool.exe
OutputBaseFilename=GrammarToolSetup
OutputDir=installer_output
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
SetupIconFile=icon.ico

[Files]
Source: "dist\GrammarTool.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\Grammar Tool"; Filename: "{app}\GrammarTool.exe"; IconFilename: "{app}\GrammarTool.exe"
Name: "{group}\Grammar Tool"; Filename: "{app}\GrammarTool.exe"
Name: "{group}\Uninstall Grammar Tool"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\GrammarTool.exe"; Description: "Launch Grammar Tool"; Flags: nowait postinstall skipifsilent
