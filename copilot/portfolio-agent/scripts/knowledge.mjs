// Optional SharePoint knowledge of the agent, set per tenant at package time.
// SHAREPOINT_KNOWLEDGE_URLS (comma or space separated SharePoint site, library or folder URLs) adds the
// OneDriveAndSharePoint capability to copilot/declarativeAgent.json and the routing rule for document contents to
// copilot/instruction.txt. Unset: nothing changes, the agent has no knowledge source. The repository keeps no tenant URL,
// and the URLs are never printed (deploy-agent passes them as a secret).
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const urls = (process.env.SHAREPOINT_KNOWLEDGE_URLS || '').split(/[\s,]+/).filter(Boolean);
if (!urls.length) {
  console.log('knowledge: SHAREPOINT_KNOWLEDGE_URLS not set, no knowledge source');
  process.exit(0);
}

const errors = [];
for (const [i, url] of urls.entries()) {
  const n = i + 1;
  let parsed;
  try { parsed = new URL(url); } catch { errors.push(`URL ${n} is not a URL`); continue; }
  if (parsed.protocol !== 'https:' || !/\.sharepoint\.com$/i.test(parsed.hostname)) errors.push(`URL ${n} is not an https SharePoint URL`);
  if (parsed.search || parsed.hash) errors.push(`URL ${n} must not contain a query or a fragment`);
}
if (errors.length) {
  errors.forEach(e => console.error('knowledge: ' + e));
  process.exit(1);
}

const agentPath = join(root, 'copilot/declarativeAgent.json');
const agent = JSON.parse(readFileSync(agentPath, 'utf8'));
agent.capabilities = (agent.capabilities || []).filter(c => c.name !== 'OneDriveAndSharePoint');
agent.capabilities.push({ name: 'OneDriveAndSharePoint', items_by_url: urls.map(url => ({ url: url.replace(/\/+$/, '') })) });
writeFileSync(agentPath, JSON.stringify(agent, null, 2) + '\n');

const RULE = '11. What a document says (contract clauses, penalties, specifications, terms of an offer, minutes) -> answer from the '
  + 'SharePoint knowledge and name the file; this is the one case answered without a component. The files carry the columns Project '
  + 'Code, Project Name, Customer, PO Number and Supplier of their record: use them to keep to the documents of the project, '
  + 'order, customer or supplier asked about. To list the files of a project use GetProjectDocuments.';
const instructionPath = join(root, 'copilot/instruction.txt');
const instructions = readFileSync(instructionPath, 'utf8');
if (!instructions.includes(RULE)) {
  writeFileSync(instructionPath, instructions.replace(/\n\nRules:/, `\n${RULE}\n\nRules:`));
}
console.log(`knowledge: OneDriveAndSharePoint on ${urls.length} SharePoint URL(s)`);
