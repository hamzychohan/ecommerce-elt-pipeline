#!/usr/bin/env bash
set -e

if [[ "$1" == "run_pipeline" ]]; then
  shift
  exec python -m orchestration.run_pipeline "$@"
fi

if [[ "$1" == "generate_report" ]]; then
  exec python -m reports.generate_report
fi

exec "$@"
