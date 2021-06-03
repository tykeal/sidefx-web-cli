# sidefx-web
Simple CLI tool for using the SideFX Web API.

## Requirements

* Python 3

## Install

```bash
pip install sidefx-web
sidefx-web --setup
```

## Example Usages

### List houdini versions

```bash
sidefx-web list-builds -h                             # Print help message
sidefx-web list-builds houdini
sidefx-web list-builds houdini-py3 --only-production  # Filter only production builds
sidefx-web list-builds houdini --version 16.5         # Filter version e.g. 16.5, 17.0
sidefx-web list-builds houdini --platform linux       # Filter platform: linux, macos, win64
```

### Download houdini
```bash
sidefx-web download -h                      # Print help message
sidefx-web download houdini 16.5 496 linux  # Download houdini 16.5 build 496 for linux
```
