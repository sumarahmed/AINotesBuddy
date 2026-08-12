#ifndef MyAppVersion
  #define MyAppVersion "2026.08.5"
#endif

#define MyAppName "NotesBuddy Desktop Companion"
#define MyAppPublisher "NotesBuddy"
#define MyAppExeName "NotesBuddyCompanion.exe"

[Setup]
AppId={{48E23B11-8A3A-4F4F-A11E-1E0238A03623}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\NotesBuddy Companion
DefaultGroupName=NotesBuddy
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=NotesBuddyCompanion-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start NotesBuddy Companion when I sign in"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\out\dist\NotesBuddyCompanion\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\MODEL_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\NotesBuddy Desktop Companion"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\NotesBuddy Desktop Companion"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "NotesBuddyCompanion"; ValueData: """{app}\{#MyAppExeName}"" --background"; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start NotesBuddy Desktop Companion"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RegDeleteValue(
      HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      'NotesBuddyCompanion'
    );
end;
