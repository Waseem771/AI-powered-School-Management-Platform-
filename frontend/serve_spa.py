import http.server
import socketserver
import os

PORT = 5173
DIRECTORY = "dist"

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # Translate the requested path to a local file path
        path = self.translate_path(self.path)
        
        # If the file doesn't exist, route to index.html (SPA Fallback)
        if not os.path.exists(path):
            self.path = '/index.html'
            
        return super().do_GET()

# Allow port reuse to avoid 'Address already in use' errors
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), SPAHandler) as httpd:
    print(f"Serving SPA on http://localhost:{PORT}")
    httpd.serve_forever()
