import os
import toml

version = "unknown"
# adopt path to your pyproject.toml
pyproject_toml_file = "pyproject.toml"
version = ""
if os.path.exists(pyproject_toml_file):
    data = toml.load(pyproject_toml_file)
    # check project.version
    if "project" in data and "version" in data["project"]:
        version = data["project"]["version"]
    # check tool.poetry.version
    elif "tool" in data and "poetry" in data["tool"] and "version" in data["tool"]["poetry"]:
        version = data["tool"]["poetry"]["version"]

# Write to version.py in the backend
version_file = "src/api/version.py"
with open(version_file, "w") as f:
    f.write(
        '"""\n'
        'Version Information\n\n'
        'This module provides the code version and is \n'
        'automatically updated by the python-semantic-release package.\n\n'
        'DO NOT EDIT IT MANUALLY.\n'
        '"""\n\n'
    )
    f.write(f'__version__ = "{version}"\n')

# Update only the version line in +layout.server.ts for the frontend
layout_file = "src/frontend/src/routes/+layout.server.ts"
with open(layout_file, "r") as f:
    lines = f.readlines()

with open(layout_file, "w") as f:
    for line in lines:
        if line.strip().startswith("version:"):
            f.write(f"\t\tversion: '{version}', // This is dynamically set in the build process\n")
        else:
            f.write(line)