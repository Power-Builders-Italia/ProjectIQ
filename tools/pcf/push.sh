#!/usr/bin/env bash
# Pushes the PCF controls of src/pcf into the OpenProject365 solution of the pac profile's environment.
# `pac pcf push` accepts one manifest per project, so each control is staged in its own folder.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/../../src/pcf" && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
for control in ${*:-WbsTreeGrid GanttChart WeeklyTimesheet TimeApproval ResourceLoad CostSummary QuoteComparison ProgressBar ProgressField}; do
  dir="$STAGE/$control"
  mkdir -p "$dir"
  cp -r "$SRC/$control" "$SRC/shared" "$SRC"/{package.json,pcfconfig.json,tsconfig.json,eslint.config.mjs} "$dir/"
  sed "s#<Name>OP365Controls</Name>#<Name>$control</Name>#" "$SRC/OP365Controls.pcfproj" > "$dir/$control.pcfproj"
  ln -s "$SRC/node_modules" "$dir/node_modules"
  rm -rf "$dir/shared"/*.test.ts
  (cd "$dir" && pac pcf push --solution-unique-name OpenProject365 --incremental false)
done
