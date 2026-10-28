#!/usr/bin/env bash
# Pushes the PCF controls of src/pcf into the OpenProject365 solution of the pac profile's environment.
# `pac pcf push` accepts one manifest per project, so each control is staged in its own folder.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/../../src/pcf" && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
for control in ${*:-WbsTreeGrid GanttChart WeeklyTimesheet TimeApproval ResourceLoad CostSummary QuoteComparison ProgressField}; do
  dir="$STAGE/$control"
  mkdir -p "$dir"
  cp -r "$SRC/$control" "$SRC/shared" "$SRC"/{package.json,pcfconfig.json,tsconfig.json,eslint.config.mjs} "$dir/"
  sed "s#<Name>OP365Controls</Name>#<Name>$control</Name>#" "$SRC/OP365Controls.pcfproj" > "$dir/$control.pcfproj"
  ln -s "$SRC/node_modules" "$dir/node_modules"
  rm -rf "$dir/shared"/*.test.ts
  # the import of the temporary wrapper solution can fail while Dataverse is still busy with a previous import or
  # publish ("There is no active transaction"): retry up to 3 times
  for attempt in 1 2 3; do
    if (cd "$dir" && pac pcf push --solution-unique-name OpenProject365 --incremental false); then break; fi
    if [ "$attempt" = 3 ]; then echo "pac pcf push failed 3 times for $control" >&2; exit 1; fi
    echo "pac pcf push failed for $control, retrying in 60 s ($attempt/3)" >&2; sleep 60
  done
done
