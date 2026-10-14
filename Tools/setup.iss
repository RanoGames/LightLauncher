[Setup]
AppName=LightLauncher
AppVersion=0.50
AppPublisher=RanoGames
DefaultDirName={autopf}\LightLauncher
DefaultGroupName=LightLauncher
SourceDir=..
OutputDir=installer_output
OutputBaseFilename=LightLauncher-setup-v0.5
SetupIconFile=mclovin.ico
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\LightLauncher.exe
RestartApplications=no
CloseApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "main.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "mclovin.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "folder.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "github.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "background.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "lang\*"; DestDir: "{app}\lang"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\LightLauncher"; Filename: "{app}\LightLauncher.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall LightLauncher"; Filename: "{uninstallexe}"
Name: "{autodesktop}\LightLauncher"; Filename: "{app}\LightLauncher.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Run]
Filename: "{app}\LightLauncher.exe"; Description: "Запустить LightLauncher"; Flags: nowait postinstall skipifsilent
