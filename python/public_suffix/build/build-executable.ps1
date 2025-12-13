Push-Location $(Split-Path $MyInvocation.MyCommand.Path)
pyinstaller --onefile ../public_suffix.py --icon ../resource/iana.ico
Pop-Location

