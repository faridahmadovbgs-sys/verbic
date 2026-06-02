; Verbic — Inno Setup script
; Build:  iscc installer.iss   →   installer_output\VerbicSetup.exe
;
; Note: MyAppId GUID is intentionally stable across renames so users who
; installed the previous "Grammar Tool" name upgrade cleanly to Verbic.

#define MyAppName       "Verbic"
#define MyAppVersion    "1.2.1"
#define MyAppPublisher  "Sand Castle LLC"
#define MyAppExeName    "Verbic.exe"
#define MyAppId         "{{2A8E1B4F-7B3C-4C26-9D1E-9F3F2C7B0A61}}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright=Copyright (C) {#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoCopyright=Copyright (C) {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}.0
DefaultDirName={autopf}\Verbic
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
OutputBaseFilename=VerbicSetup
OutputDir=installer_output
Compression=lzma2
SolidCompression=yes
; Per-user install by default (no UAC prompt); user can elevate via the dialog
; if they want it for all users.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=icon.ico
LicenseFile=EULA.txt
WizardStyle=modern
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64compatible
; Sign installer + uninstaller once a cert is configured. Configure SignTool
; under Tools -> Configure Sign Tools in the Inno Setup IDE, then uncomment:
; SignTool=mysigntool
; SignedUninstaller=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startupicon"; Description: "Start {#MyAppName} when Windows starts"; GroupDescription: "Auto-start:"; Flags: unchecked

[Files]
; --onedir build: ship the whole dist\Verbic folder (Verbic.exe + _internal\
; with python3xx.dll and dependencies). recursesubdirs pulls in _internal.
Source: "dist\Verbic\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "EULA.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillGrammarTool"

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // Kill the new and the legacy executable name so the installer can
  // overwrite the old binary when upgrading from the previous "Grammar Tool"
  // name to "Verbic".
  Exec('taskkill.exe', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill.exe', '/F /IM GrammarTool.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;
