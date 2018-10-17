# Project-X
RESTful Geocode proxy service.  Used as a proxy for 3rd party geocode providers.  Single threaded for single process multiple deployment in microservices environment or as a limited load stand-alone service.

# Development Status
Version 0.1 (ALPHA)  
Python 3.7+ recommended  
- (lower versions may work, but project not currently tested against multiple Python versions)

# Features
Multiple 3rd party geocode provider support, configurable via JSON properties file.

# Quick Start
```
$ python3 geoproxy.py
```

# Command Line Interface
```
usage: geoproxy.py [-h] [--path REL_PATH] [--addr SRV_ADDR] [--port SRV_PORT]
                   [--cctl MAX_AGE] [--debug]

A service that proxies 3rd party geocode providers.

optional arguments:
  -h, --help       show this help message and exit
  --path REL_PATH  relative URL path of service (default: '/geocode?')
  --addr SRV_ADDR  bind address (default: '')
  --port SRV_PORT  port (default: 8000)
  --cctl MAX_AGE   cache-control max-age in secs (default: 0)
  --debug          run debug mode against test data
```

FYI debug mode use JSON data files with naming convention '{provider name}_sample.json' where {provider name} comes from the providers.json props file.  Both the sample data file and the provider props must exist.
