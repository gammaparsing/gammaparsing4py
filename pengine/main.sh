#!/bin/bash


# Checking if a command was specified
command=$1
shift 1

if ! [ -n "$command" ]; then
    echo "No command was specified. Aborting..."
    exit
fi

# Getting the options
verbose=false

while getopts ":v" opt; do
    case ${opt} in
        v) verbose=true;;
        *) 
        echo -e "Option not recognized: \x1b[1;31m-${OPTARG}\x1b[0m"
        exit
        ;;
    esac
done
shift $((OPTIND-1))

# Handling verbosity
if ! $verbose; then
    exec 3>&1 4>&2 &>/dev/null
fi

# Getting the project's directory
mainPath=$(readLink -f "$0")
projectDir=$(dirname "$(dirname "$mainPath")")

cd "$projectDir"

# Greeting the user
echo -e "<---- \x1b[1;31mProject\x1b[0m\x1b[1;34mENGINE\x1b[0m ---->"
echo -e "> Project dir: \x1b[38;5;111m$projectDir\x1b[0m"

# Running the command
commandPath=$projectDir/pengine/commands/$command.sh

if ! [ -e "$commandPath" ]; then
    echo -e "No command found with name \x1b[1;31m$command\x1b[0m" >&3
    echo -e "Run command \x1b[1;31mhelp\x1b[0m to see all available commands" >&3
    exit
fi
if ! [ -n "$*" ]; then
    echo -e "> Running command \x1b[1;33m$command\x1b[0m"
else
    echo -e "> Running command \x1b[1;33m$command\x1b[0m with arguments \x1b[1;35m$*\x1b[0m"
fi

if ! $verbose; then
    exec 1>&3 2>&4
fi

bash "$commandPath" "$projectDir" "$verbose" $*