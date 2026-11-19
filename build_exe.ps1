# Génère l'exécutable unique ES-PIGC.exe (PyInstaller) dans dist\
# Prérequis : Python 3.9 avec les versions de requirements.txt + `pip install pyinstaller==6.16.0`
#             et les modèles Excel dans ressources\modeles\ (non versionnés).
# Usage     : .\build_exe.ps1            (ou .\build_exe.ps1 -Python C:\chemin\vers\python.exe)
param([string]$Python = "python")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "ressources\modeles\*.xlsx")) {
    throw "Modèles Excel introuvables dans ressources\modeles\ : copiez-les avant de compiler."
}

# PyInstaller écrit sa progression sur stderr : ne pas la traiter comme une erreur fatale
# (le succès est vérifié via le code de sortie juste après).
$ErrorActionPreference = "Continue"

# --hidden-import win32timezone : pywin32 l'importe dynamiquement pour convertir les dates Outlook
# (ReceivedTime). Sans lui, PyInstaller ne l'embarque pas et la collecte des mails échoue
# (« No module named 'win32timezone' »).
& $Python -X utf8 -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name ES-PIGC `
    --icon "ressources/icones/favicon.ico" `
    --add-data "app/styles;app/styles" `
    --add-data "ressources;ressources" `
    --add-data "app/ressources;app/ressources" `
    --collect-submodules app `
    --hidden-import win32timezone `
    --exclude-module tkinter --exclude-module IPython --exclude-module pytest `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller a échoué (code $LASTEXITCODE)" }

Get-FileHash "dist\ES-PIGC.exe" -Algorithm SHA256 | Format-List
