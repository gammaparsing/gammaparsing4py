import os
import sys
import json
import importlib

# Handling given arguments
projectDir: str = sys.argv[1]
launchConfigName: str = sys.argv[2]
sys.argv = [sys.argv[0]] + sys.argv[3:]

if not launchConfigName:
    print("No launch configuration was specified. Aborting")
    sys.exit()

# Loading project metadata
with open(
    os.path.join(projectDir, "project.json"), "r", encoding="utf-"
) as inputStream:
    projectMetadata: dict = json.load(inputStream)

launchConfigurations = projectMetadata.get("launch-configurations", {})

# Handling missing launch config name
if launchConfigName not in launchConfigurations:
    print(
        "No launch configuration found with name \x1b[1;31m{}\x1b[0m. Aborting...".format(
            launchConfigName
        )
    )
    sys.exit()

# Adding sub projects to path
for subProject in os.listdir(os.path.join(projectDir, "subprojects")):
    sys.path.append(
        os.path.join(projectDir, "subprojects", subProject, "src", "python")
    )

sys.path.append(os.path.join(projectDir, "pengine", "python", "engine-libs"))

# Preparing runtime utils
from pengine_utils import PEngineUtils

PEngineUtils.setup(projectDir)

# Importing the target module
importlib.import_module(launchConfigurations[launchConfigName]["target"])
