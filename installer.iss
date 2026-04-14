; HAMAL Inno Setup Installer Script
; Creates a standard Windows installer from PyInstaller one-folder build

#define MyAppName "HAMAL"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Omer Dahan"
#define MyAppURL "https://github.com/Omer-Dahan/H.A.M.A.L"
#define MyAppExeName "HAMAL.exe"

[Setup]
; NOTE: AppId uniquely identifies this application.
; Do not use the same AppId in installers for other applications.
; Double braces required for proper GUID handling.
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Output configuration
OutputDir=installer_output
OutputBaseFilename=HAMAL_Setup_{#MyAppVersion}
; Compression
Compression=lzma2
SolidCompression=yes
; Visual style
WizardStyle=modern
; Admin required for Program Files installation
PrivilegesRequired=admin
; Prevent running installer while app is running
AppMutex=HAMAL_SingleInstance
SetupIconFile=src\hamal\ui\assets\icons\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startup"; Description: "Launch HAMAL on Windows startup"; GroupDescription: "Additional options:"

[Files]
; Copy the icon file specifically to the root for reliable shortcut creation
Source: "src\hamal\ui\assets\icons\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
; Install all files from PyInstaller one-folder build
; Source path is relative to this .iss file location
Source: "dist\HAMAL\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcuts (now with icon)
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop shortcut (checked by default)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"

[Registry]
; Run on startup registry key
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "HAMAL"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
; Option to launch after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up any files created by the app in the install directory
Type: filesandordirs; Name: "{app}"
; Clean up user data on uninstall
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"

[Code]
// Show message about user data location on first install
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // User data location reminder (optional)
  end;
end;

// check for existing data and ask user
function InitializeSetup(): Boolean;
var
  DataDir: String;
  Res: Integer;
begin
  Result := True;
  DataDir := ExpandConstant('{localappdata}\{#MyAppName}');
  
  // Check if data directory exists
  if DirExists(DataDir) then
  begin
    // Ask user if they want to reset
    Res := MsgBox('Existing data found for ' + '{#MyAppName}' + '.' + #13#10 + #13#10 + 'Do you want to DELETE all existing projects and settings to start fresh?' + #13#10 + #13#10 + '• Click YES to delete everything (Clean Install)' + #13#10 + '• Click NO to keep your existing projects', mbConfirmation, MB_YESNO);
    
    // If user chose YES, delete the directory
    if Res = IDYES then
    begin
      try
        DelTree(DataDir, True, True, True);
        // Create the directory anew to ensure it's clean and ready
        CreateDir(DataDir);
      except
        // Ignore errors if file is locked (rare during install)
      end;
    end;
  end;
end;
