from pathlib import Path
p=Path('/etc/nginx/sites-available/ai-agent')
s=p.read_text()
assert s.count('location / {') == 1
s=s.replace('location / {', '''location = /oauth2/start { return 404; }
    location = /oauth2/callback { return 404; }
    location /oauth2/ {
        proxy_pass http://127.0.0.1:4180;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Auth-Request-Redirect $scheme://$host$request_uri;
    }
    location = /oauth2/auth {
        internal;
        proxy_pass http://127.0.0.1:4180;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Original-URL $scheme://$host$request_uri;
        proxy_set_header Content-Length "";
        proxy_pass_request_body off;
    }
    location / {
        auth_request /oauth2/auth;
        error_page 401 =403 /oauth2/sign_in;
''')
p.with_suffix('.before-gate').write_text(p.read_text())
p.write_text(s)
