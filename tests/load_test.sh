#!/usr/bin/env bash
#
# load_test.sh - Apache bench wrapper for the Synapse load balancer.
#
# Sends a burst of HTTP GET requests at the load balancer so that the
# round-robin distribution can be observed in the response bodies (each backend
# reports its own hostname) and the throughput/latency figures can be recorded.
#
# Usage:
#   ./tests/load_test.sh [-n REQUESTS] [-c CONCURRENCY] [-u URL]
#
# Examples:
#   ./tests/load_test.sh
#   ./tests/load_test.sh -n 5000 -c 100
#   ./tests/load_test.sh -u http://localhost:8080/health

set -euo pipefail

REQUESTS=1000
CONCURRENCY=50
URL="http://localhost:8080/"

usage() {
    cat <<'EOF'
Usage: load_test.sh [-n REQUESTS] [-c CONCURRENCY] [-u URL]

Load-test the Synapse load balancer with Apache bench (ab).

Options:
  -n REQUESTS     Total number of requests to send        (default: 1000)
  -c CONCURRENCY  Number of concurrent requests           (default: 50)
  -u URL          Target URL                              (default: http://localhost:8080/)
  -h, --help      Show this help message and exit

Examples:
  ./tests/load_test.sh -n 5000 -c 100
  ./tests/load_test.sh -u http://localhost:8080/health
EOF
}

# Handle the long form up front, since getopts only understands single-dash flags.
for arg in "$@"; do
    case "${arg}" in
        --help)
            usage
            exit 0
            ;;
    esac
done

while getopts ":n:c:u:h" opt; do
    case "${opt}" in
        n) REQUESTS="${OPTARG}" ;;
        c) CONCURRENCY="${OPTARG}" ;;
        u) URL="${OPTARG}" ;;
        h)
            usage
            exit 0
            ;;
        :)
            echo "Error: option -${OPTARG} requires an argument." >&2
            usage >&2
            exit 1
            ;;
        \?)
            echo "Error: unknown option -${OPTARG}." >&2
            usage >&2
            exit 1
            ;;
    esac
done

if ! command -v ab >/dev/null 2>&1; then
    echo "Error: 'ab' (Apache bench) is not installed or not on PATH." >&2
    echo "" >&2
    echo "Install it with:" >&2
    echo "  macOS:         brew install apache-httpd && brew link --overwrite httpd" >&2
    echo "  Debian/Ubuntu: sudo apt-get install -y apache2-utils" >&2
    echo "  Fedora/RHEL:   sudo dnf install -y httpd-tools" >&2
    exit 1
fi

if ! [[ "${REQUESTS}" =~ ^[0-9]+$ ]] || [[ "${REQUESTS}" -lt 1 ]]; then
    echo "Error: -n must be a positive integer (got '${REQUESTS}')." >&2
    exit 1
fi

if ! [[ "${CONCURRENCY}" =~ ^[0-9]+$ ]] || [[ "${CONCURRENCY}" -lt 1 ]]; then
    echo "Error: -c must be a positive integer (got '${CONCURRENCY}')." >&2
    exit 1
fi

if [[ "${CONCURRENCY}" -gt "${REQUESTS}" ]]; then
    echo "Warning: concurrency (${CONCURRENCY}) exceeds request count (${REQUESTS})." >&2
fi

echo "Synapse load test"
echo "  URL:         ${URL}"
echo "  Requests:    ${REQUESTS}"
echo "  Concurrency: ${CONCURRENCY}"
echo ""
echo "Running: ab -n ${REQUESTS} -c ${CONCURRENCY} ${URL}"
echo ""

ab -n "${REQUESTS}" -c "${CONCURRENCY}" "${URL}"