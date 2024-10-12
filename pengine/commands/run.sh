projectDir=$1
verbose=$2
launchConfig=$3

pythonVersion=$(python --version 2>/dev/null)

if ! [ -n "$pythonVersion" ]; then
    echo -e "> \x1b[1;31mPython is not installed\x1b[0m. Aborting..."
    exit
fi

if $verbose; then
    echo -e "> Python version found: \x1b[1;34m$pythonVersion\x1b[0m"
fi

python -B "$projectDir/pengine/python/launcher.py" "$projectDir" "$launchConfig" ${@:4}