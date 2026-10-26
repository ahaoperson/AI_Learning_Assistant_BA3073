#!/usr/bin/env bash
set -u
umask 077
read -r -p 'ECS public IPv4 address: ' ECS_PUBLIC_IP
{
  printf 'AI Learning Assistant ECS Web Interface Check\n'
  date '+Time (local): %Y-%m-%dT%H:%M:%S%z'
  date -u '+Time (UTC): %Y-%m-%dT%H:%M:%SZ'
  printf 'Machine: %s\n' "$(hostname)"
  printf 'Operating system: %s\n' "$(uname -sr)"
  printf 'CPU architecture: %s\n' "$(uname -m)"
  printf 'ECS login user: %s\n' "$(whoami)"
  printf 'Website URL: http://%s:14242/ui/\n' "$ECS_PUBLIC_IP"
  sudo docker --version
  printf '\nDocker application container:\n'
  sudo docker ps -a --filter publish=14242 --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
  printf '\nWebsite URL check from ECS:\n'
  UI_HTTP_STATUS=$(curl --noproxy '*' -sS --connect-timeout 5 --max-time 15 \
    -o /dev/null -w '%{http_code}' "http://${ECS_PUBLIC_IP}:14242/ui/")
  CURL_EXIT_CODE=$?
  printf 'HTTP status: %s\n' "$UI_HTTP_STATUS"
  if [ "$CURL_EXIT_CODE" -eq 0 ] && [ "$UI_HTTP_STATUS" = '200' ]; then
    printf 'Website URL check: PASS\n'
  else
    printf 'Website URL check: FAIL (curl exit code: %s)\n' "$CURL_EXIT_CODE"
  fi
} 2>&1 | tee ecs-docker-check.txt
