#ifndef AppVersion
  #error AppVersion must be provided with /DAppVersion=...
#endif
#ifndef SourceFolder
  #error SourceFolder must be provided with /DSourceFolder=...
#endif
#ifndef OutputFolder
  #error OutputFolder must be provided with /DOutputFolder=...
#endif

#define AppName "Thonny Classroom"
#define AppExeName "thonny\thonny.exe"

[Setup]
AppId={{E6498F18-6C90-49D5-9326-78F7468B04A7}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Thonny Classroom
AppPublisherURL=https://thonny.org/
AppSupportURL=https://thonny.org/
DefaultDirName={localappdata}\Programs\Thonny Classroom
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputFolder}
OutputBaseFilename=thonny-classroom-{#AppVersion}-windows-x64-setup
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
SetupLogging=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\{#AppExeName}
LicenseFile=..\license-for-win-installer.txt
WizardImageFile=..\screenshot_with_logo_semidark.bmp
WizardSmallImageFile=..\small_logo.bmp

[Files]
Source: "{#SourceFolder}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}\thonny"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}\thonny"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
