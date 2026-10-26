# BA3073 deployment workflow

This is a preparation guide, not evidence of a completed deployment.
Student: 徐兆豪 (2330036168). Report language: English.
Intended GitHub owner: ahaoperson.

## 1. Local verification

Start Docker Desktop, then from the project root:

```sh
docker compose -p ai-learning-assistant up --build -d
curl -fsS http://127.0.0.1:14242/health
bash scripts/check-local-ui.sh --open
```

Wait for a healthy container. Capture the working browser interface with the
address bar visible. Register with your real BNBU email. Enter your Qwen API key
in model settings; do not put it in screenshots or this repository.

## 2. ACR and ECS

Use an actual Aliyun ECS instance, not a substitute hosting platform. Determine
its CPU architecture (`uname -m`) before building. For x86_64 ECS use linux/amd64;
for aarch64 ECS use linux/arm64. On the local Mac:

```sh
export ACR_IMAGE='REPLACE_WITH_ACR_REGISTRY/NAMESPACE/REPOSITORY:ba3073'
# Run docker login with the registry host shown by ACR; enter credentials privately.
docker buildx build --platform linux/amd64 --provenance=false --sbom=false -t "$ACR_IMAGE" --load .
docker push "$ACR_IMAGE"
```

On ECS, install Docker Engine and Compose following the official instructions
for its actual OS. Copy this project without .git, secrets, runtime data or
local dependency directories. Log in to ACR privately and set the same ACR_IMAGE.

```sh
export AILA_BIND_IP=0.0.0.0
docker compose -f compose.ecs.yml -p ai-learning-assistant pull
docker compose -f compose.ecs.yml -p ai-learning-assistant up -d
```

Restrict inbound TCP 14242 to the student's current public IP (/32). Keep SSH
restricted as well. Open http://ECS_PUBLIC_IP:14242/ui/ on the student's computer
and capture the working interface with the address bar. Run
`bash scripts/check-ecs-ui.sh` directly on ECS and keep ecs-docker-check.txt.
The teacher's script makes a request from ECS to its own public IP; a security
group allowing only the student's IP can block that request. Diagnose and record
any failure honestly; do not label a loopback request as a public-IP test or open
14242 to the world to make the log pass.

## 3. Domain, TLS and additional access control

Create an A record for a domain/subdomain you control, pointing to ECS. Configure
Nginx and Certbot for that real hostname. Open TCP 80/443. Add a separate proxy
access-control layer and test both rejection and successful access.

Integration note: the app uses Authorization: Bearer for API requests. A naive
Nginx auth_basic on every route conflicts with that header. The chosen access
layer must preserve authenticated API access; check login, generation, polling
and downloads through the proxy, not just the static login page. Final proxy
configuration will be selected and tested when cloud resources are available.

After the proxy works, return the application to loopback:

```sh
export AILA_BIND_IP=127.0.0.1
docker compose -f compose.ecs.yml -p ai-learning-assistant up -d
```

Remove the security-group rule exposing 14242 and verify it is unreachable from
outside. Capture successful HTTPS access after the additional access-control
check, with the hostname and browser address bar visible.

## Report and submission

Use the deployed AI Learning Assistant, Essay mode, to generate the report using
actual logs and evidence. The revised instructions are in
backend/pipelines/essay_html.py. Include authentic screenshots and verify the
exported PDF is no more than 20 pages in total. Do not submit an unverified draft.

Submit the report, full source repository URL, local-ui-check.txt and
ecs-docker-check.txt. Never submit .env*, Qwen_API, data/, workspace/,
node_modules/, .venv/, __pycache__/, *.pyc or credentials. Keep generated reports
and evidence outside the source repository.
