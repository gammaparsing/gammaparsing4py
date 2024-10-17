projectDir=$1
verbose=$2

command=$3

if ! [ -n "$3" ]; then 
    echo "No command specified"
    exit
fi

if [ "$command" == "show-tag-history" ]; then
    echo -e $(git for-each-ref refs/tags --sort=creatordate --format '%(creatordate:format:'\(%Y-%m-%d\)') %(tag) %(contents)')
fi