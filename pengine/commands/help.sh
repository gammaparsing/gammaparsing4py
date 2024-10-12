projectDir=$1
echo -e "List of all available commands:"
for file in $(find "$projectDir/pengine/commands" -name "*.sh" -printf "%f\0"| xargs -0 echo)
do
    echo -e "> \x1b[1;31m${file::-3}\x1b[0m"
done
