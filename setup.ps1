# Change PYTHON_HOME if needed
$PYTHON_HOME = "C:\Python27"
$VENV_HOME = ".\.venv\"
$VENV_ACTIVATION_SCRIPT = "$VENV_HOME\Scripts\Activate.ps1"
Write-Output "*************Look PYTHON in: $PYTHON_HOME"
Write-Output "*************Expected VENV dir in: $VENV_HOME"

$ISERROR = 0
$RESULT

trap {
    # error handling goes here, $_ contains the error record
    Write-Output "Error on: "
    Write-Output $_

    $script:ISERROR = 1

}

Write-Output "Starting..."
Write-Output "Calling python to create .venv folder..."

$RESULT = Invoke-Expression $PYTHON_HOME"\python.exe -m virtualenv .venv 2>&1"

if ($ISERROR)
{
    Write-Output "*** ERROR calling python *** Output from command: $RESULT"
    Write-Output "Calling python to create .venv folder...ERROR"
}
else
{
    Write-Output "Calling python to create .venv folder...DONE"
}

if ( $ISERROR -le 0 ) 
{
    Write-Output "Activating VENV..."
    Invoke-Expression "$VENV_ACTIVATION_SCRIPT 2>&1" 
    if ($ISERROR)
    {
        Write-Output "*** ERROR Activating VENV *** Output from command: $RESULT"
        Write-Output "Activating VENV...ERROR"
    }
    else
    {
        Write-Output "Activating VENV...DONE"
    }
}

if ($ISERROR) 
{
    Write-Output "*** ERROR *** Installing stuff from requirement.txt due to error from last command"
}
else
{
    Write-Output "Installing stuff from requirement.txt ..."
    Invoke-Expression "pip install -r requirements.txt"
    Write-Output "Installing stuff from requirement.txt ...DONE"
}