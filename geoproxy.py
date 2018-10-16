import argparse
import logging
import ipaddress
import http.server
import urllib.request
import json


class Response:
    STATUS_KEY = "status"
    STATUS_OK = "ok"
    STATUS_FAIL = "fail"
    STATUS_DEBUG = "debug"
    MESSAGE_KEY = "msg"
    LOCATION_KEY = "loc"

class GeoServiceHandler(http.server.BaseHTTPRequestHandler):
    """
    This subclass is the HTTP request handler for the Geocode Proxy Service
    """
    def _set_headers(self, code):
        """
        Sets the HTTP response header for this service.

        :param code: The HTTP status code to send in the response header
        """
        global _max_age

        self.send_response(code)
        self.send_header('Content-type', 'application/json')

        if code == 200 and _max_age > 0:
            self.send_header('Cache-Control', 'public, max-age={}'.format(_max_age))

        self.end_headers()

    def do_GET(self):
        """
        Handles GET requests from clients.
        """
        global _rel_path
        try:
            # parse path from GET
            if not self.path.startswith(_rel_path):
                self._set_headers(404)
                json_obj = json.dumps({Response.STATUS_KEY: Response.STATUS_FAIL, Response.MESSAGE_KEY: "Unknown resource path '{}'".format(self.path)})
                self.wfile.write(bytes(json_obj, 'utf8'))
                return

            # parse addr parameter from GET
            addr = None
            params = dict(urllib.parse.parse_qsl(self.path.split("?")[1], True))
            if 'addr' in params and params['addr']:
                addr = params['addr']
            else:
                self._set_headers(400)
                json_obj = json.dumps({Response.STATUS_KEY: Response.STATUS_FAIL, Response.MESSAGE_KEY: "Missing required 'addr' parameter in proxy service request"})
                self.wfile.write(bytes(json_obj, 'utf8'))
                return

            # call geocode provider(s)
            code, content = self._get_geolocation(addr)

            # handle geocode provider response
            if code == 200:
                self._set_headers(200)
                self.wfile.write(bytes(content, 'utf8'))
            else:
                self._set_headers(502)
                json_obj = json.dumps({Response.STATUS_KEY: Response.STATUS_FAIL, Response.MESSAGE_KEY: "An error occurred with 3rd party geocode providers"})
                self.wfile.write(bytes(json_obj, 'utf8'))
        except Exception as ex:
            logger.error('Unexpected runtime error caught!\n- error: {}'.format(str(ex)))

            self._set_headers(500)
            json_obj = json.dumps({Response.STATUS_KEY: Response.STATUS_FAIL, Response.MESSAGE_KEY: "An unknown error occurred with the geocode proxy service"})
            self.wfile.write(bytes(json_obj, 'utf8'))

    @classmethod
    def _encode_params(cls, url_path, get_params):
        """
        URL encode parameters and concatenate absolute URL string.

        :param url_path: Base URL path.
        :param get_params: Parameter dict to be URL encoded.
        :return: Absolute URL path with URL encoded parameters.
        """
        url_params = urllib.parse.urlencode(get_params)
        return '{}{}'.format(url_path, url_params)

    @classmethod
    def _unpack_json(cls, json_dict, key_path):
        """
        Return the dictionary found at the end of a the JSON dictionary's key path.

        :param json_dict: Dictionary representation of a JSON object.
        :param key_path: The space-separated key path to follow into the JSON dictionary.
        :return: The dictionary object found at the key path.
        """
        data_dict = json_dict

        try:
            for key in key_path.split():
                if key.isdecimal():
                    key = int(key)
                data_dict = data_dict[key]
        except:
            return None

        return data_dict

    @classmethod
    def _get_geolocation(cls, addr):
        """
        Resolve address with 3rd party geocode provider(s).

        :param addr: Physical address to resolve into geocode location.
        :return: Resulting HTTP response code and JSON content from geocode resolution.
        """
        debug_log = []  # trace for debug mode

        addr = urllib.parse.urlencode({'': addr})[1:]  # URL encoded address value
        for provider in _providers:
            req_url = urllib.request.Request('{}{}'.format(provider['base_url'], addr))
            try:
                resp_json = ""

                if _dbg_mode:
                    # read sample responses for provider
                    json_file = provider['name'] + '_sample.json'
                    with open(json_file) as json_data:
                        resp_json = json.load(json_data)
                else:
                    # call provider API
                    resp = urllib.request.urlopen(req_url)
                    encoding = resp.info().get_content_charset('utf-8')
                    data = resp.read()
                    resp_json = data.decode(encoding)
                    resp_json = json.loads(resp_json)

                # validate response
                stat_val = GeoServiceHandler._unpack_json(resp_json, provider['stat_key'])
                if stat_val is None or str(stat_val) != provider['stat_val']:
                    logger.error("Invalid response status\n- provider: {}\n- Got '{}', expected '{}'".format(provider['name'], stat_val, provider['stat_val']))
                    continue

                coords = GeoServiceHandler._unpack_json(resp_json, provider['res_path'])
                if coords is None:
                    logger.error("Could not parse coordinates\n- provider: {}\n- res_path: {}".format(provider['name'], provider['res_path']))
                else:
                    loc_keys = provider['loc_keys'].split()
                    if _dbg_mode:
                        debug_log.append('provider: {}, lat: {}, lon: {}'.format(provider['name'],
                                                                                        coords[loc_keys[0]],
                                                                                        coords[loc_keys[1]]))
                    else:
                        return 200, json.dumps({Response.STATUS_KEY: Response.STATUS_OK, Response.LOCATION_KEY: "lat: {}, lon: {}".format(coords[loc_keys[0]], coords[loc_keys[1]])})
            except urllib.error.URLError as ex:
                logger.error("Error fetching URL '{}'\n{}".format(req_url.get_full_url(), ex.reason))
                continue

        if _dbg_mode:
            return 200, json.dumps({Response.STATUS_KEY: Response.STATUS_DEBUG, Response.MESSAGE_KEY: debug_log})

        return 502, json.dumps({Response.STATUS_KEY: Response.STATUS_FAIL, Response.MESSAGE_KEY: "Error retrieving geocode from providers"})


def init_providers():
    # retrieve geo provider configs
    provider_file = 'providers.json'  # config file for 3rd party geo providers
    provider_list = 'geo_providers'   # top-level list of provider dictionaries
    provider_keys = ['name',          # provider name
                     'base_url',      # base URL including prepopulated API keys, ending with provider address field
                     'res_path',      # successful response path to provider's lat & lon coordinates
                     'loc_keys',      # provider's lat & lon keys (found in result of above 'res_path')
                     'stat_key',      # provider's path to response status
                     'stat_val']      # expected value for successful response

    with open(provider_file) as json_data:
        json_data = json.load(json_data)
        if provider_list not in json_data:
            raise IOError("Missing '{}' in providers.json config file".format(provider_list))

        i = 0
        for item in json_data[provider_list]:
            for key in provider_keys:
                if key not in item or not item[key]:
                    raise IOError("Missing '{}' for item '{}' in providers.json config file".format(key, i))
            i += 1

        global _providers
        _providers = json_data[provider_list]


def run(server_class=http.server.HTTPServer, handler_class=GeoServiceHandler):
    """
    Main entry point for running Geocode Proxy Service

    :param server_class: HTTPServer (derived) class.
    :param handler_class: BaseHTTPRequestHandler (derived) class.
    :return: Value to return in exit().
    """
    # validate relative path
    try:
        global _rel_path
        if not _rel_path:  # relative URL path to access the service
            raise ValueError
    except ValueError:
        logger.error("Invalid relative URL path value: {}\n- Value should be valid relative URL path, starting with '/' and ending with '?'".format(_rel_path))
        return 1

    # validate address value
    try:
        global _srv_addr
        if _srv_addr != '':  # '' = any, or valid IP address
            ipaddress.ip_address(_srv_addr)
    except ValueError:
        logger.error(
            'Invalid server address value: {}\n- Value should be valid IP address'.format(_srv_addr))
        return 1

    # validate port value
    try:
        global _srv_port
        if _srv_port < 1024 or _srv_port > 49151:  # user port range for servers typically 1024 to 49151
            raise ValueError
    except ValueError:
        logger.error('Invalid server port value: {}\n- Value should be between 1024 to 49151, inclusive'.format(_srv_port))
        return 1

    # validate cache-control max-age value
    try:
        global _max_age
        if _max_age < 0:  # max-age for cache control must be 0 or greater
            raise ValueError
    except ValueError:
        logger.error('Invalid cache-control value: {}\n- Value of max-age must be 0 or greater'.format(_max_age))
        return 1

    # init http server
    server_address = (_srv_addr, _srv_port)
    httpd = server_class(server_address, handler_class)

    # start http server
    try:
        httpd.serve_forever()
    except Exception as ex:
        logger.error('Unexpected server shutdown:\n{}'.format(str(ex)))
        return 1

"""
Globals
"""
_rel_path = '/geocode?'  # default relative URL path of service
_srv_addr = ''           # default service address
_srv_port = 8000         # default service port
_max_age = 0             # default cache-control value (0 = no cache-control)
_dbg_mode = False        # run debug mode against test data

_providers = []          # provider list

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # read cli args
    parser = argparse.ArgumentParser(description='A service that proxies 3rd party geocode providers.')
    parser.add_argument('--path', action='store', default=_rel_path, dest='rel_path',
                        help='relative URL path of service (default: \'{}\')'.format(_rel_path))
    parser.add_argument('--addr', action='store', default=_srv_addr, dest='srv_addr',
                        help='bind address (default: \'{}\')'.format(_srv_addr))
    parser.add_argument('--port', action='store', default=_srv_port, dest='srv_port', type=int,
                        help='port (default: {})'.format(_srv_port))
    parser.add_argument('--cctl', action='store', default=_max_age, dest='max_age', type=int,
                        help='cache-control max-age in secs (default: {})'.format(_max_age))
    parser.add_argument('--debug', action='store_true', default=False, dest='dbg_mode',
                        help='run debug mode against test data')
    args = parser.parse_args()

    _rel_path = args.rel_path
    _srv_addr = args.srv_addr
    _srv_port = args.srv_port
    _max_age = args.max_age
    _dbg_mode = args.dbg_mode

    try:
        # init providers from config file
        init_providers()

        # run service (forever)
        exit(run())
    except KeyboardInterrupt:
        logger.info('Process killed by user')
        exit(0)
    except FileNotFoundError:
        logger.error('Missing providers.json config file')
        exit(1)
    except IOError as ex:
        logger.error(str(ex))
        exit(1)
