#!/usr/bin/env python3
"""
Serve a markdown doc as HTML via pandoc + a local HTTP server.
Usage: python3 tools/serve_doc.py docs/agentrack-adsr-manifest.md
"""

import http.server
import os
import subprocess
import sys
import tempfile
import threading
import webbrowser

PORT = 8765

CSS = """
<style>
  body {
    max-width: 860px;
    margin: 48px auto;
    padding: 0 32px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 16px;
    line-height: 1.65;
    color: #1a1a1a;
    background: #fafafa;
  }
  h1 { font-size: 2em; border-bottom: 2px solid #222; padding-bottom: 0.3em; }
  h2 { font-size: 1.4em; border-bottom: 1px solid #ddd; padding-bottom: 0.2em; margin-top: 2em; }
  h3 { font-size: 1.15em; margin-top: 1.5em; }
  pre {
    background: #1e1e1e;
    color: #d4d4d4;
    border-radius: 6px;
    padding: 1em 1.2em;
    overflow-x: auto;
    font-size: 0.88em;
    line-height: 1.5;
  }
  code {
    background: #efefef;
    border-radius: 3px;
    padding: 0.15em 0.35em;
    font-size: 0.9em;
  }
  pre code { background: none; padding: 0; font-size: inherit; }
  blockquote {
    border-left: 4px solid #888;
    margin: 0;
    padding: 0.5em 1.2em;
    color: #555;
    background: #f4f4f4;
    border-radius: 0 4px 4px 0;
  }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; }
  th, td { border: 1px solid #ccc; padding: 0.5em 0.8em; text-align: left; }
  th { background: #f0f0f0; font-weight: 600; }
  tr:nth-child(even) { background: #f8f8f8; }
  a { color: #0066cc; }
  hr { border: none; border-top: 1px solid #ddd; margin: 2em 0; }
</style>
"""

def build_html(md_path):
    result = subprocess.run(
        ["pandoc", md_path, "--from=markdown", "--to=html5", "--standalone=false"],
        capture_output=True, text=True, check=True
    )
    body = result.stdout
    title = os.path.basename(md_path)
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>{CSS}</head><body>{body}</body></html>"


def make_handler(html_content):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_content.encode())

        def log_message(self, fmt, *args):
            pass  # suppress request logging

    return Handler


def main():
    md_path = sys.argv[1] if len(sys.argv) > 1 else "docs/agentrack-adsr-manifest.md"
    md_path = os.path.abspath(md_path)

    print(f"Rendering: {md_path}")
    html = build_html(md_path)

    handler = make_handler(html)
    server = http.server.HTTPServer(("127.0.0.1", PORT), handler)

    url = f"http://127.0.0.1:{PORT}"
    print(f"Serving at {url}")
    threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
