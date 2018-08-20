# resin-release-tool
This tool is to set release canary in resin.io

## Installation
```
pip install git+ssh://git@github.com/mobilityhouse/resin-release-tool.git
```

## Usage
```
Usage: resin-release-tool [OPTIONS]

Options:
  --app TEXT      Application name
  --token TEXT    Resin.io auth token
  --release TEXT  Commit hash of the release in resin to set application
  --canary TEXT   Commit hash of the release in resin for canary
  --releases      Show last releases
  --help          Show this message and exit.
```
