#!/usr/bin/env python3
"""Artha Analytics reverse proxy — injects branding overrides into Metabase HTML."""
import http.server
import http.client
import os
import gzip
import io

METABASE_PORT = 3001
PROXY_PORT = int(os.environ.get("PORT", "3000"))

INJECT_SCRIPT = b"""<script>
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
        conn = http.client.HTTPConnection("127.0.0.1", METABASE_PORT, timeout=300)
        body = None
        if "Content-Length" in self.headers:
            body = self.rfile.read(int(self.headers["Content-Length"]))

        # Forward headers, force identity encoding so we get uncompressed data
        fwd = {}
        for k, v in self.headers.items():
            lk = k.lower()
            if lk not in ("host", "transfer-encoding", "accept-encoding"):
                fwd[k] = v
        fwd["Accept-Encoding"] = "identity"

        try:
            conn.request(self.command, self.path, body=body, headers=fwd)
            resp = conn.getresponse()
        except Exception as e:
            self.send_error(502, str(e))
            return

        data = resp.read()
        ct = ""
        skip = {"transfer-encoding", "content-encoding", "content-length",
                "content-security-policy", "content-security-policy-report-only"}

        self.send_response(resp.status)
        for k, v in resp.getheaders():
            lk = k.lower()
            if lk == "content-type":
                ct = v
            if lk not in skip:
                self.send_header(k, v)

        # Inject script into HTML responses
        if "text/html" in ct and b"</head>" in data:
            data = data.replace(b"</head>", INJECT_SCRIPT + b"</head>", 1)

        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        conn.close()

    do_GET = do_proxy
    do_POST = do_proxy
    do_PUT = do_proxy
    do_DELETE = do_proxy
    do_PATCH = do_proxy
    do_OPTIONS = do_proxy

    def do_HEAD(self):
        conn = http.client.HTTPConnection("127.0.0.1", METABASE_PORT, timeout=300)
        fwd = {}
        for k, v in self.headers.items():
            lk = k.lower()
            if lk not in ("host", "transfer-encoding"):
                fwd[k] = v
        try:
            conn.request("HEAD", self.path, headers=fwd)
            resp = conn.getresponse()
        except Exception as e:
            self.send_error(502, str(e))
            return
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            self.send_header(k, v)
        self.end_headers()
        conn.close()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"[artha-proxy] listening on :{PROXY_PORT}, proxying to :{METABASE_PORT}", flush=True)
    server = http.server.HTTPServer(("0.0.0.0", PROXY_PORT), ProxyHandler)
    server.serve_forever()
