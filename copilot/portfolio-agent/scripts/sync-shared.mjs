// Copies the pure business logic shared with the PCF controls (src/pcf/shared) into src/shared/projectiq,
// so the agent computes progress, costs, critical path and resource load with exactly the same rules.
// The copies are generated (git-ignored): edit the originals under src/pcf/shared.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const source = join(root, '..', '..', 'src', 'pcf', 'shared');
const target = join(root, 'src', 'shared', 'projectiq');
const FILES = ['dates.ts', 'wbs.ts', 'cpm.ts', 'cost.ts', 'load.ts', 'timesheet.ts', 'approval.ts'];

mkdirSync(target, { recursive: true });
for (const file of FILES) {
  const text = readFileSync(join(source, file), 'utf8');
  writeFileSync(join(target, file), `/* eslint-disable */\n// Generated from src/pcf/shared/${file} by scripts/sync-shared.mjs. Do not edit.\n${text}`);
}
console.log(`sync-shared: ${FILES.length} files copied to src/shared/projectiq`);
