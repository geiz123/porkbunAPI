# porkbunAPI

# UnifiPorkbunDDNS.py
- Uses python 2.7 because Unifi OS has 2.7
- Code format = `yapf`
- `virtualenv` instead of `venv`
    - Install `python2.7` first then install `virutalenv` with: `python -m pip install virtualenv`
    - Then run `setup.ps1` to setup the `venv` folder

- Also need to install correct python extension so vscode will be able to run debug
    - https://stackoverflow.com/a/73666581/3614460
    - In addition you need to install or revert `Pylance` to `2021.9.3`
    - Might also need to install `Debugpy Old` and uninstall `Python Debugger` that came with the `Python` extension

# Sending Email
Currently sending using `Postmark` and `AWS SES` as the backup.

## Postmark

## AWS SES
