import * as React from 'react';
import { Button, Combobox, Field, Input, Option, Text, Textarea } from '@fluentui/react-components';
import { Add16Regular, Delete16Regular, DocumentArrowUp16Regular } from '@fluentui/react-icons';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, FollowUp, Footer, Info, Kpi, KpiGrid, Loading, OpenInApp, Section, Shell } from '../kit';
import { hours } from '../format';
import {
  canCreate, draftFrom, matchByName, parseAmount, planProject, validateDraft,
  type DraftIssue, type DraftIssueCode, type ExtractedProject, type ProjectDraft, type WbsDraftLine,
} from '../../logic/projectDraft';
import { fileSize } from '../../logic/documents';
import { NoDocumentLibraryError, type Choice } from '../../services/ProjectIQService';
import { promptFor } from '../../intents';
import { recordUrl } from '../../settings';
import { culture, strings } from '../../i18n';

export interface CreateProjectProps extends ExtractedProject {
  documentName?: string;
  customer?: string;
  projectManager?: string;
}

const FILL: React.CSSProperties = { width: '100%', minWidth: 0 };
/** Height of a Field label and its gap, to line the delete button up with the inputs. */
const LABEL_HEIGHT = 22;
/** Options shown by a picker while the user types (customers and users can be thousands). */
const MAX_OPTIONS = 30;

let lineSeq = 0;
const newKey = (): string => `w${++lineSeq}`;

type Step = 'edit' | 'review' | 'done';

interface Receipt {
  id: string;
  code: string;
  nodes: number;
  total: number;
  nodeError?: string;
  fileUrl?: string;
  documentError?: string;
}

/** Combobox over many choices: filters while typing, keeps the chosen id. */
const Picker: React.FC<{ choices: Choice[]; value?: string; placeholder: string; onChange: (id?: string) => void }> = ({ choices, value, placeholder, onChange }) => {
  const selected = choices.filter(c => c.id === value)[0];
  const [text, setText] = React.useState(selected?.name || '');
  React.useEffect(() => { setText(selected?.name || ''); }, [selected?.id]);
  const q = text.trim().toLowerCase();
  const options = (q && q !== selected?.name.toLowerCase() ? choices.filter(c => c.name.toLowerCase().indexOf(q) >= 0) : choices).slice(0, MAX_OPTIONS);
  return (
    <Combobox value={text} selectedOptions={value ? [value] : []} placeholder={placeholder} style={FILL} input={{ style: FILL }}
      onChange={e => { setText(e.target.value); if (!e.target.value) onChange(undefined); }}
      onOptionSelect={(_, d) => { onChange(d.optionValue); setText(d.optionText || ''); }}>
      {options.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
    </Combobox>
  );
};

export const CreateProjectView: React.FC<CreateProjectProps> = props => {
  const { wide, ready, openLink, setModelContext } = useAgent();
  const str = strings();
  const t = str.newProject;
  const state = useServiceData(async (service, settings) => {
    const [customers, users] = await Promise.all([service.customers(), service.users()]);
    return { customers, users, settings };
  }, []);
  const [draft, setDraft] = React.useState<ProjectDraft>(() => draftFrom(props, newKey));
  const [file, setFile] = React.useState<File | undefined>();
  const [step, setStep] = React.useState<Step>('edit');
  const [progress, setProgress] = React.useState<string | undefined>();
  const [error, setError] = React.useState<Error | undefined>();
  const [receipt, setReceipt] = React.useState<Receipt>();
  const fileInput = React.useRef<HTMLInputElement>(null);
  const prefilled = React.useRef(false);

  // Customer and project manager named in the document become the choice when exactly one record matches.
  React.useEffect(() => {
    if (!state.data || prefilled.current) return;
    prefilled.current = true;
    const customer = matchByName(state.data.customers, props.customer);
    const manager = matchByName(state.data.users, props.projectManager);
    setDraft(d => ({ ...d, customerId: d.customerId || customer?.id, managerId: d.managerId || manager?.id }));
  }, [state.data]);

  const issues = validateDraft(draft, !!file);
  const message = (code: DraftIssueCode, key?: string): string | undefined =>
    (issues.filter(i => i.code === code && i.key === key).length ? t.issues[code] : undefined);
  const lineIssue = (key: string): DraftIssue | undefined => issues.filter(i => i.key === key)[0];
  const projectIssues = issues.filter(i => !i.key);
  const errors = issues.filter(i => i.severity === 'error').length;
  const totalHours = draft.lines.reduce((s, l) => s + (parseAmount(l.budgetHours) || 0), 0);
  const name = (list: Choice[] | undefined, id?: string): string => list?.filter(c => c.id === id)[0]?.name || '';

  React.useEffect(() => {
    setModelContext(`New ProjectIQ project from ${props.documentName ? 'the document ' + props.documentName : 'a document'}. `
      + `Draft: name "${draft.name}", customer ${name(state.data?.customers, draft.customerId) || 'not chosen'}, `
      + `project manager ${name(state.data?.users, draft.managerId) || 'not chosen'}, dates ${draft.startDate || '?'} to ${draft.endDate || '?'}, `
      + `${draft.lines.length} WBS nodes (${draft.lines.map(l => `${l.code} ${l.name}`).join('; ')}). `
      + `Missing or wrong: ${issues.filter(i => i.severity === 'error').map(i => i.code).join(', ') || 'nothing'}. Document file selected: ${file ? 'yes' : 'no'}. `
      + `Step: ${step}. Nothing is created until the user selects Confirm in the card`
      + (receipt ? `; created project ${receipt.code} in status Offer with ${receipt.nodes} WBS nodes.` : '.'));
  }, [draft, file, step, receipt, state.data]);

  const patch = (p: Partial<ProjectDraft>): void => setDraft(d => ({ ...d, ...p }));
  const patchLine = (key: string, p: Partial<WbsDraftLine>): void => setDraft(d => ({ ...d, lines: d.lines.map(l => (l.key === key ? { ...l, ...p } : l)) }));
  const addLine = (): void => setDraft(d => {
    const top = d.lines.reduce((max, l) => Math.max(max, Number(l.code.split('.')[0]) || 0), 0);
    return { ...d, lines: [...d.lines, { key: newKey(), code: String(top + 1), name: '', budgetHours: '', startDate: '', endDate: '' }] };
  });

  const create = async (): Promise<void> => {
    if (!canCreate(issues)) return;
    setError(undefined);
    const plan = planProject(draft);
    let project: { id: string; code: string } | undefined;
    try {
      const { service } = await ready;
      setProgress(t.creatingProject);
      project = await service.createProject(plan);
      const created = project;
      const ids: Record<string, string> = {};
      let nodeError: string | undefined;
      for (let i = 0; i < plan.nodes.length; i++) {
        const node = plan.nodes[i];
        setProgress(t.creatingNodes(i + 1, plan.nodes.length));
        try {
          ids[node.code] = await service.createNode(created.id, node, node.parentCode ? ids[node.parentCode] : undefined);
        } catch (e) {
          nodeError = (e as Error).message;
          break;
        }
      }
      let fileUrl: string | undefined;
      let documentError: string | undefined;
      if (file) {
        setProgress(t.savingDocument);
        try {
          fileUrl = (await service.saveProjectDocument(created.id, plan.name, file.name, file)).fileUrl;
        } catch (e) {
          documentError = e instanceof NoDocumentLibraryError ? t.noLibrary : (e as Error).message;
        }
      }
      setReceipt({ id: created.id, code: created.code, nodes: Object.keys(ids).length, total: plan.nodes.length, nodeError, fileUrl, documentError });
      setStep('done');
    } catch (e) {
      setError(e as Error);
    } finally {
      setProgress(undefined);
    }
  };

  const busy = progress !== undefined;
  return (
    <Shell eyebrow={t.eyebrow} title={draft.name || str.intents.CreateProjectFromDocument.title}
      subtitle={props.documentName ? t.subtitle(props.documentName) : t.noDocument}>
      {state.error && <ErrorBar error={state.error} />}
      {error && <ErrorBar error={error} />}
      {state.loading && !state.data && <Loading />}
      {step === 'done' && receipt && state.data && (
        <>
          <Info intent={receipt.nodeError ? 'warning' : 'success'} title={t.created(receipt.code)}>
            {t.createdText(receipt.nodes)}
            {receipt.nodeError ? ` ${t.nodesFailed(receipt.nodes, receipt.total)} (${receipt.nodeError})` : ''}
          </Info>
          {receipt.fileUrl && <Info intent="success">{t.documentSaved}</Info>}
          {receipt.documentError && <Info intent="warning" title={t.documentFailed}>{receipt.documentError}</Info>}
          <Footer>
            <OpenInApp url={recordUrl(state.data.settings, 'op365_project', receipt.id)} />
            {receipt.fileUrl && <Button size="small" icon={<DocumentArrowUp16Regular />} onClick={() => openLink(receipt.fileUrl!)}>{t.openDocument}</Button>}
            <FollowUp prompt={promptFor('GetProjectHealth', receipt.code)}>{t.health}</FollowUp>
            <FollowUp prompt={promptFor('GetProjectDocuments', receipt.code)}>{t.documents}</FollowUp>
          </Footer>
        </>
      )}
      {state.data && step !== 'done' && (
        <>
          <KpiGrid>
            <Kpi label={t.toComplete} value={String(errors)} tone={errors ? 'warning' : 'success'} />
            <Kpi label={t.nodes} value={String(draft.lines.length)} />
            <Kpi label={t.hoursTotal} value={hours(totalHours)} />
          </KpiGrid>
          {step === 'edit' && (
            <>
              <Section title={t.project}>
                <Field label={t.name} required validationMessage={message('noName')}>
                  <Input value={draft.name} style={FILL} input={{ style: FILL }} onChange={(_, d) => patch({ name: d.value })} />
                </Field>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  <Field label={t.customer} required style={{ minWidth: 200, flexGrow: 1, flexBasis: 0 }}
                    validationMessage={message('noCustomer') && (props.customer ? `${t.issues.noCustomer} ${t.inDocument(props.customer)}` : t.issues.noCustomer)}>
                    <Picker choices={state.data.customers} value={draft.customerId} placeholder={t.search} onChange={id => patch({ customerId: id })} />
                  </Field>
                  <Field label={t.manager} required style={{ minWidth: 200, flexGrow: 1, flexBasis: 0 }}
                    validationMessage={message('noManager') && (props.projectManager ? `${t.issues.noManager} ${t.inDocument(props.projectManager)}` : t.issues.noManager)}>
                    <Picker choices={state.data.users} value={draft.managerId} placeholder={t.search} onChange={id => patch({ managerId: id })} />
                  </Field>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  <Field label={t.startDate} required style={{ width: 160 }} validationMessage={message('noStart')}>
                    <Input type="date" value={draft.startDate} style={FILL} input={{ style: FILL }} onChange={(_, d) => patch({ startDate: d.value })} />
                  </Field>
                  <Field label={t.endDate} required style={{ width: 160 }} validationMessage={message('noEnd') || message('endBeforeStart')}>
                    <Input type="date" value={draft.endDate} style={FILL} input={{ style: FILL }} onChange={(_, d) => patch({ endDate: d.value })} />
                  </Field>
                  <Field label={t.contractValue} style={{ width: 160 }} validationMessage={message('badValue')}>
                    <Input value={draft.contractValue} inputMode="decimal" style={FILL} input={{ style: FILL }} onChange={(_, d) => patch({ contractValue: d.value })} />
                  </Field>
                </div>
                <Field label={t.description}>
                  <Textarea value={draft.description} resize="vertical" onChange={(_, d) => patch({ description: d.value })} />
                </Field>
              </Section>
              <Section title={t.wbs}>
                <Text size={200}>{t.wbsHelp}</Text>
                {draft.lines.map(l => {
                  const issue = lineIssue(l.key);
                  const depth = l.code.split('.').length - 1;
                  return (
                    <div key={l.key} style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'flex-start', paddingLeft: wide ? Math.min(depth, 4) * 16 : 0 }}>
                      <Field label={t.code} style={{ width: 80, flexShrink: 0 }}
                        validationMessage={issue && ['badCode', 'duplicateCode', 'noParent'].indexOf(issue.code) >= 0 ? t.issues[issue.code] : undefined}>
                        <Input value={l.code} style={FILL} input={{ style: FILL }} onChange={(_, d) => patchLine(l.key, { code: d.value.trim() })} />
                      </Field>
                      <Field label={t.phase} style={{ minWidth: 160, flexGrow: 2, flexBasis: 0 }} validationMessage={message('noNodeName', l.key)}>
                        <Input value={l.name} style={FILL} input={{ style: FILL }} onChange={(_, d) => patchLine(l.key, { name: d.value })} />
                      </Field>
                      <Field label={t.budgetHours} style={{ width: 96, flexShrink: 0 }} validationMessage={message('badHours', l.key)}>
                        <Input value={l.budgetHours} inputMode="decimal" style={FILL} input={{ style: FILL }} onChange={(_, d) => patchLine(l.key, { budgetHours: d.value })} />
                      </Field>
                      {wide && (
                        <>
                          <Field label={t.start} style={{ width: 150, flexShrink: 0 }}
                            validationMessage={message('badNodeDates', l.key) || message('nodeOutsideProject', l.key)}
                            validationState={message('nodeOutsideProject', l.key) ? 'warning' : undefined}>
                            <Input type="date" value={l.startDate} style={FILL} input={{ style: FILL }} onChange={(_, d) => patchLine(l.key, { startDate: d.value })} />
                          </Field>
                          <Field label={t.end} style={{ width: 150, flexShrink: 0 }}>
                            <Input type="date" value={l.endDate} style={FILL} input={{ style: FILL }} onChange={(_, d) => patchLine(l.key, { endDate: d.value })} />
                          </Field>
                        </>
                      )}
                      <Button appearance="subtle" icon={<Delete16Regular />} style={{ marginTop: LABEL_HEIGHT }} aria-label={t.removeNode}
                        onClick={() => setDraft(d => ({ ...d, lines: d.lines.filter(x => x.key !== l.key) }))} />
                    </div>
                  );
                })}
                <Footer>
                  <Button size="small" icon={<Add16Regular />} onClick={addLine}>{t.addNode}</Button>
                </Footer>
              </Section>
              <Section title={t.document}>
                {props.documentName && !file && <Text size={200}>{t.fileHint(props.documentName)}</Text>}
                <input ref={fileInput} type="file" style={{ display: 'none' }}
                  onChange={e => { setFile(e.target.files?.[0] || undefined); e.target.value = ''; }} />
                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
                  <Button size="small" icon={<DocumentArrowUp16Regular />} onClick={() => fileInput.current?.click()}>{file ? t.changeFile : t.chooseFile}</Button>
                  {file && <Text size={200}>{file.name} · {fileSize(file.size, culture())}</Text>}
                </div>
                <Text size={200}>{t.fileHelp}</Text>
              </Section>
              {projectIssues.filter(i => i.severity === 'warning').map(i => <Info key={i.code} intent="warning">{t.issues[i.code]}</Info>)}
              <Footer>
                <Button appearance="primary" disabled={!canCreate(issues)} onClick={() => setStep('review')}>{t.review}</Button>
              </Footer>
            </>
          )}
          {step === 'review' && (
            <>
              <Info title={t.reviewTitle}>
                {t.reviewText(draft.lines.length)} {file ? t.withFile(file.name) : ''}
              </Info>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                <li><Text size={200}>{draft.name} · {name(state.data.customers, draft.customerId)} · {name(state.data.users, draft.managerId)}</Text></li>
                <li><Text size={200}>{draft.startDate} → {draft.endDate}{draft.contractValue ? ` · ${draft.contractValue}` : ''}</Text></li>
                {planProject(draft).nodes.map(n => (
                  <li key={n.code}><Text size={200}>{n.code} {n.name}{n.budgetHours !== undefined ? ` · ${hours(n.budgetHours)}` : ''}</Text></li>
                ))}
              </ul>
              {issues.filter(i => i.severity === 'warning').map((i, n) => <Info key={n} intent="warning">{t.issues[i.code]}</Info>)}
              {progress && <Loading label={progress} />}
              <Footer>
                <Button appearance="primary" disabled={busy} onClick={() => { create().catch(() => undefined); }}>{busy ? str.common.saving : t.create}</Button>
                <Button disabled={busy} onClick={() => setStep('edit')}>{str.common.back}</Button>
              </Footer>
            </>
          )}
          <Text size={200}>{t.note}</Text>
        </>
      )}
    </Shell>
  );
};
