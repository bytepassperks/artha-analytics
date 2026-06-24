#!/usr/bin/env python3
"""Artha Analytics reverse proxy — injects branding overrides into Metabase HTML."""
import http.server
import urllib.request
import urllib.error
import os
import re
import sys

METABASE_PORT = 3001
PROXY_PORT = int(os.environ.get("PORT", "3000"))

INJECT_SCRIPT = """<script>
(function(){
  try{var e=document.getElementById('_metabaseBootstrap');
  if(e){var d=JSON.parse(e.textContent);
  d['help-link']='hidden';d['show-metabase-links']=false;
  d['application-name']='Artha Analytics';
  d['token-features']=Object.assign(d['token-features']||{},{whitelabel:true});
  e.textContent=JSON.stringify(d)}}catch(x){}
  document.title='Artha Analytics';
  var _f=window.fetch;
  window.fetch=function(){return _f.apply(this,arguments).then(function(r){
  if(r.url&&r.url.indexOf('/api/session/properties')!==-1){
  return r.clone().json().then(function(d){d['help-link']='hidden';
  d['show-metabase-links']=false;d['application-name']='Artha Analytics';
  d['token-features']=Object.assign(d['token-features']||{},{whitelabel:true});
  return new Response(JSON.stringify(d),{status:r.status,statusText:r.statusText,headers:r.headers})})}
  return r})}
})();
</script>"""


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_proxy(self):
        url = f"http://127.0.0.1:{METABASE_PORT}{self.path}"
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "transfer-encoding")}
        body = None
        if "Content-Length" in self.headers:
            body = self.rfile.read(int(self.headers["Content-Length"]))
        req = urllib.request.Request(url, data=body, headers=headers, method=self.command)
        try:
            resp = urllib.request.urlopen(req, timeout=300)
        except urllib.error.HTTPError as e:
            resp = e
        except Exception as e:
            self.send_error(502, str(e))
            return

        self.send_response(resp.status)
        ct = resp.headers.get("Content-Type", "")
        is_html = "text/html" in ct
        skip_headers = {"transfer-encoding", "content-encoding", "content-length",
                        "content-security-policy", "content-security-policy-report-only"}
        for k, v in resp.headers.items():
            if k.lower() not in skip_headers:
                self.send_header(k, v)

        data = resp.read()
        if is_html and b"</head>" in data:
            data = data.replace(b"</head>", INJECT_SCRIPT.encode() + b"</head>", 1)

        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_proxy
    do_POST = do_proxy
    do_PUT = do_proxy
    do_DELETE = do_proxy
    do_PATCH = do_proxy
    do_OPTIONS = do_proxy
    do_HEAD = do_proxy

    def log_message(self, format, *args):
        pass  # suppress noisy logging


if __name__ == "__main__":
    print(f"[artha-proxy] listening on :{PROXY_PORT}, proxying to :{METABASE_PORT}", flush=True)
    server = http.server.HTTPServer(("0.0.0.0", PROXY_PORT), ProxyHandler)
    server.serve_forever()
