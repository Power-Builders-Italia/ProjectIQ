// Consistency checks of the agent before packaging: every component is bundled and exposed by the agent,
// tool names are unique and short enough, the intent catalog covers every tool, the instructions fit the limit.
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const json = path => JSON.parse(readFileSync(join(root, path), 'utf8'));
const errors = [];

const config = json('config/config.json');
const agent = json('config/copilot-agent.json').agents[0];
const declarative = json('copilot/declarativeAgent.json');
const intents = readFileSync(join(root, 'src/shared/intents.ts'), 'utf8');
const instructions = readFileSync(join(root, 'copilot/instruction.txt'), 'utf8');
const bundled = config.bundles['projectiq-portfolio-agent'].components.map(c => c.manifest.replace(/^\.\//, ''));

const tools = new Set();
for (const folder of readdirSync(join(root, 'src/copilotComponents'))) {
  const file = readdirSync(join(root, 'src/copilotComponents', folder)).find(f => f.endsWith('.manifest.json'));
  const path = `src/copilotComponents/${folder}/${file}`;
  const manifest = json(path);
  if (!bundled.includes(path)) errors.push(`${path} is not in config/config.json`);
  if (!agent.components.includes(manifest.id)) errors.push(`${manifest.alias} (${manifest.id}) is not in config/copilot-agent.json`);
  for (const tool of manifest.tools) {
    if (tools.has(tool.name)) errors.push(`duplicate tool ${tool.name}`);
    tools.add(tool.name);
    if (tool.name.length > 40) errors.push(`tool name ${tool.name} longer than 40 characters`);
    if (!intents.includes(`key: '${tool.name}'`)) errors.push(`tool ${tool.name} missing from src/shared/intents.ts`);
    if (!instructions.includes(tool.name)) errors.push(`tool ${tool.name} not routed in copilot/instruction.txt`);
  }
}
if (agent.components.length !== tools.size) errors.push('config/copilot-agent.json lists components that do not exist');
if (declarative.conversation_starters.length > 6) errors.push('more than 6 conversation starters');
if (instructions.length > 8000) errors.push(`instruction.txt is ${instructions.length} characters (limit 8000)`);

if (errors.length) {
  errors.forEach(e => console.error('validate-agent: ' + e));
  process.exit(1);
}
console.log(`validate-agent: ${tools.size} tools OK`);
