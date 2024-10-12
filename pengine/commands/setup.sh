projectDir=$1
verbose=$2

cd "$projectDir"
shift 2
python -B "$projectDir/pengine/python/setup.py" $@