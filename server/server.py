import http.server
import socketserver
import ssl

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'x-api-key,Content-Type')
        super().end_headers()

def main():
    PORT = 8000
    Handler = CORSRequestHandler

    # Create an SSL context
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    
    # Load your SSL certificate and key
    context.load_cert_chain(certfile='/etc/letsencrypt/live/worthyrae.com/fullchain.pem', 
                            keyfile='/etc/letsencrypt/live/worthyrae.com/privkey.pem')

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        # Wrap the socket with the SSL context
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        print("serving at port", PORT)
        httpd.serve_forever()

if __name__ == '__main__':
    main()
