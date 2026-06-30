#!/usr/bin/env bash
set -euo pipefail

docker exec pra-redis redis-cli SET pra:system:initialized true >/dev/null
docker exec pra-redis redis-cli SET pra:system:project PortfolioRiskAgent >/dev/null
docker exec pra-redis redis-cli PING
