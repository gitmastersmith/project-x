# Project-X
RESTful Geocode proxy service.  Used as a proxy for 3rd party geocode providers.  Single threaded for single process multiple deployment in microservices environment or as a limited load stand-alone service.

# Development Status
Version 0.1 (ALPHA)  
Python 3.7+ recommended  
- lower versions may work, but project not currently tested against multiple Python versions

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

* debug mode use JSON data files with naming convention '{provider name}_sample.json' where {provider name} comes from the providers.json props file.  Both the sample data file and the provider props must exist.

# Providers Props File

Sample file:
```
{
  "geo_providers" : [
    {
      "name" : "google",
      "base_url" : "https://maps.googleapis.com/maps/api/geocode/json?key=0123456789abcdef&address=",
      "res_path" : "results 0 geometry location",
      "loc_keys" : "lat lng",
      "stat_key" : "status",
      "stat_val" : "OK"
    },
    {
      "name" : "here",
      "base_url" : "https://geocoder.api.here.com/6.2/geocode.json?app_id=0123456789abcdef&app_code=0123456789abcdef&searchtext=",
      "res_path" : "Response View 0 Result 0 Location DisplayPosition",
      "loc_keys" : "Latitude Longitude",
      "stat_key" : "Response View 0 Result 0 Relevance",
      "stat_val" : "1"
    }
  ]
}
```

* Must contain 'geo_providers' as top element
* Each provider entry must contain:
  * name: provider name
  * base_url: base URL including prepopulated API keys, ending with provider address field
  * res_path: successful response path to provider's latitude & longitude coordinates
  * loc_keys: provider's latitude & longitude keys (found in result of above 'res_path')
  * stat_key: provider's path to response status
  * stat_val: expected value for successful response

FYI 'path' values above (ie, res_path & stat_key) uses space-separated values, with strings used to access JSON string keys and ints used to index JSON array elements

