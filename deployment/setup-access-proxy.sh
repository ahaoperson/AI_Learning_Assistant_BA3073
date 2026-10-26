set -eu
cd /opt/ai-learning-assistant
curl -fsSL https://github.com/oauth2-proxy/oauth2-proxy/releases/download/v7.15.5/oauth2-proxy-v7.15.5.linux-amd64.tar.gz -o /tmp/oauth2-proxy.tar.gz
curl -fsSL https://github.com/oauth2-proxy/oauth2-proxy/releases/download/v7.15.5/oauth2-proxy-v7.15.5.linux-amd64.tar.gz-sha256sum.txt -o /tmp/oauth2-proxy.sha256
expected=$(cut -d ' ' -f1 /tmp/oauth2-proxy.sha256)
actual=$(sha256sum /tmp/oauth2-proxy.tar.gz | cut -d ' ' -f1)
test "$expected" = "$actual"
tar -xzf /tmp/oauth2-proxy.tar.gz -C /tmp
install -m 755 /tmp/oauth2-proxy-v7.15.5.linux-amd64/oauth2-proxy /usr/local/bin/oauth2-proxy
umask 077
cookie_secret=$(python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')
cat > proxy-secrets/oauth2-proxy.cfg <<CFG
http_address = "127.0.0.1:4180"
provider = "github"
client_id = "password-only-no-oauth-client"
client_secret = "password-only-no-oauth-secret"
redirect_url = "https://yigehaoperson.duckdns.org/oauth2/callback"
email_domains = ["*"]
htpasswd_file = "/opt/ai-learning-assistant/proxy-secrets/users.htpasswd"
display_htpasswd_form = true
upstreams = ["static://202"]
cookie_secret = "$cookie_secret"
cookie_name = "__Host-aila_gate"
cookie_secure = true
cookie_httponly = true
cookie_samesite = "lax"
cookie_expire = "8h"
reverse_proxy = true
set_xauthrequest = true
skip_provider_button = false
CFG
cat > /etc/systemd/system/aila-access-proxy.service <<'UNIT'
[Unit]
Description=AI Learning Assistant independent access gate
After=network-online.target
[Service]
ExecStart=/usr/local/bin/oauth2-proxy --config=/opt/ai-learning-assistant/proxy-secrets/oauth2-proxy.cfg
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now aila-access-proxy
systemctl is-active aila-access-proxy
curl -s -o /dev/null -w 'Gate sign-in HTTP %{http_code}\n' http://127.0.0.1:4180/oauth2/sign_in
