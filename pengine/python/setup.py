import re
import subprocess
import sys
from setuptools import setup, find_packages

try:
    version = subprocess.check_output(
        ["git", "describe", "--tags", "--exact-match", "master"]
    ).decode()
except Exception as e:
    print("No tag can be found to describe \x1b[1;31mmaster\x1b[0m")
    sys.exit(1)

versionPattern = re.compile(
    r"v(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<patch>[0-9]+)(-(?P<status>[a-zA-Z0-9]+))?$"
)
versionMatch = versionPattern.match(version)

if versionMatch is None:
    print(
        "Invalid tag format for the setup script: \x1b[1;31m{}\x1b[0m".format(version)
    )
    sys.exit()

if versionMatch.group("status") is not None:
    print(
        "Current version has the following status: \x1b[1;31m{}\x1b[0m".format(
            versionMatch.group("status")
        )
    )
    sys.exit(1)

usedVersion = "{}.{}.{}".format(
    versionMatch.group("major"),
    versionMatch.group("minor"),
    versionMatch.group("patch"),
)

print("> Current project production version: {}".format(usedVersion))


setup(
    name="gammaparsing4py",
    version=usedVersion,
    packages=find_packages("subprojects/gammaparsing4py/src/python"),
    package_dir={"": "subprojects/gammaparsing4py/src/python"},
    author="Florent Guille",
    author_email="asgeltaren@gmail.com",
)
