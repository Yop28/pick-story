#!/bin/bash
# run-pick.sh: Entry point to execute the shot picker script.

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Run the python script from the script's directory
python3 "$DIR/pick_shots.py" "$@"
