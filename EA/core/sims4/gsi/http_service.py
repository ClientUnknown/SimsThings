import sockettry:
    import threading
    _threading_enabled = True
except ImportError:
    _threading_enabled = False
    import dummy_threading as threadingimport timeimport sims4.gsi.dispatcherimport sims4.logimport sims4.core_servicestry:
    import urllib.parse
except:
    passlogger = sims4.log.Logger('GSI')try:
    import http.server
except ImportError:

    class http:

        class server:

            class BaseHTTPRequestHandler:

                def __init__(self):
                    pass

            class HTTPServer:

                def __init__(self):
                    pass
JSONP_CALLBACK = 'callback'LOCAL_HOST = 'localhost'HTTP_SERVER_TIMEOUT = 0.001
class GameHttpHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, log_format, *args):
        pass

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'content-type')
        self.send_header('Content-Length', '0')
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

    def do_GET(self):
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            clean_path = parsed_url.path.strip('/')
            try:
                if parsed_url.query:
                    params = urllib.parse.parse_qs(parsed_url.query)
                    for (key, value) in params.items():
                        if value[0] == 'true':
                            params[key] = True
                        elif value[0] == 'false':
                            params[key] = False
                        else:
                            params[key] = value[0]
                else:
                    params = None
            except Exception:
                logger.exception('Unable to parse kwargs from query string:\n{}', parsed_url.query)
                params = None
            if params is None:
                callback_string = None
                response = sims4.gsi.dispatcher.handle_request(clean_path, params)
            else:
                callback_string = params.pop(JSONP_CALLBACK, None)
                response = sims4.gsi.dispatcher.handle_request(clean_path, params)
            if response is None:
                self.send_response(404)
                return
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            if callback_string:
                response = callback_string + '(' + response + ')'
            self.write_string(response)
            return
        except ConnectionAbortedError:
            pass

    def write_string(self, string):
        self.wfile.write(bytes(string, 'UTF-8'))

def _get_host_address():
    host_name = socket.gethostname()
    try:
        return socket.gethostbyname(host_name)
    except socket.gaierror:
        return socket.gethostbyname(LOCAL_HOST)

def _try_create_http_server(host_address, port, http_handler):
    try:
        return http.server.HTTPServer((host_address, port), http_handler)
    except OSError:
        host_address = socket.gethostbyname(LOCAL_HOST)
        return http.server.HTTPServer((host_address, port), http_handler)
if _threading_enabled:

    class HttpService(sims4.service_manager.Service):

        def __init__(self):
            self._server_thread = None
            self._server_lock = threading.Lock()
            self._http_server = None

        def on_tick(self):
            pass

        def stop(self):
            self.stop_server()

        def start_server(self, callback):
            if self._server_thread is None:
                self._server_thread = threading.Thread(target=self._http_server_loop, args=(callback,), name='HTTP Server')
                self._server_thread.start()
            else:
                callback(self._http_server)

        def stop_server(self):
            if self._server_thread is not None:
                with self._server_lock:
                    if self._http_server is not None:
                        self._http_server.socket.close()
                        self._http_server = None
                    self._server_thread = None

        def _http_server_loop(self, callback=None):
            host_address = _get_host_address()
            port = 0
            if self._http_server is None:
                with self._server_lock:
                    self._http_server = _try_create_http_server(host_address, port, GameHttpHandler)
                    self._http_server.timeout = HTTP_SERVER_TIMEOUT
            if callback is not None:
                callback(self._http_server)
            while self._http_server is not None:
                with self._server_lock:
                    self._http_server.handle_request()
                time.sleep(0.1)

else:

    class HttpService(sims4.service_manager.Service):

        def __init__(self):
            self._http_server = None

        def on_tick(self):
            if self._http_server is None:
                return
            self._http_server.handle_request()

        def stop(self):
            self.stop_server()

        def start_server(self, callback):
            if self._http_server is None:
                host_address = _get_host_address()
                port = 0
                self._http_server = _try_create_http_server(host_address, port, GameHttpHandler)
                self._http_server.timeout = HTTP_SERVER_TIMEOUT
            if callback is not None:
                callback(self._http_server)

        def stop_server(self):
            if self._http_server is not None:
                self._http_server.socket.close()
                self._http_server = None

def start_http_server(callback):
    service = sims4.core_services.http_service()
    if service is not None:
        service.start_server(callback)

def stop_http_server():
    service = sims4.core_services.http_service()
    if service is not None:
        service.stop_server()
