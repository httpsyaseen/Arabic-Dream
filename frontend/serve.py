"""Static server for the frontend during development.

    python frontend/serve.py [port]

`python -m http.server` answers conditional requests with 304 and sends no
Cache-Control, so a browser keeps running the JavaScript it downloaded an hour
ago. That produced a genuinely confusing bug — a new dream showing the previous
dream's answer — because the page was executing an older version of the code.

This sends no-store, so every reload gets what is actually on disk. In
production the right rule is different: hashed filenames served immutable, with
the HTML itself no-cache. See docs/DEPLOY.md.
"""

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_response(self, code, message=None):
        # Never answer "you already have it" — that is the whole point.
        super().send_response(200 if code == 304 else code, message)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
    handler = partial(NoCacheHandler, directory=str(Path(__file__).parent))
    print(f"frontend on http://0.0.0.0:{port}  (no-store)")
    ThreadingHTTPServer(("0.0.0.0", port), handler).serve_forever()
