import * as React from 'react';
import {
  Badge, Button, Checkbox, Dropdown, Field, Input, Option, Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text,
} from '@fluentui/react-components';
import { Add16Regular, ChevronLeft16Regular, ChevronRight16Regular, Delete16Regular } from '@fluentui/react-icons';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, Footer, Info, Kpi, KpiGrid, Loading, OpenInApp, Shell } from '../kit';
import { hours, shortDate, weekday } from '../format';
import { buildTimesheet, STATUS, weekStart } from '../../projectiq/timesheet';
import { canConfirm, planSubmission, resolveDay, type DraftIssue, type DraftLine } from '../../logic/timesheetDraft';
import type { Choice } from '../../services/ProjectIQService';
import { listUrl } from '../../settings';
import { strings } from '../../i18n';
import { timeStatusLabel } from '../labels';

export interface SubmitTimesheetProps {
  project?: string;
  hours?: number;
  date?: string;
  wbsNode?: string;
  notes?: string;
  weekOf?: string;
}

/** Inputs take the width of their field: the native size of an input pushed the Hours box over the Notes field. */
const FILL: React.CSSProperties = { width: '100%', minWidth: 0 };
/** Height of a Field label and its gap, to line the delete button up with the inputs. */
const LABEL_HEIGHT = 22;

const STATUS_COLOR: Record<number, 'informative' | 'warning' | 'success' | 'danger'> = {
  [STATUS.draft]: 'informative', [STATUS.submitted]: 'warning', [STATUS.approved]: 'success', [STATUS.rejected]: 'danger',
};

const matchChoice = (choices: Choice[], text?: string): Choice | undefined => {
  const q = (text || '').trim().toLowerCase();
  if (!q) return undefined;
  const hits = choices.filter(c => c.name.toLowerCase().indexOf(q) >= 0);
  return hits.length === 1 ? hits[0] : choices.filter(c => c.name.toLowerCase().split(' ')[0] === q)[0];
};

let lineSeq = 0;
const newKey = (): string => `l${++lineSeq}`;

type Step = 'edit' | 'review' | 'done';

export const SubmitTimesheetView: React.FC<SubmitTimesheetProps> = props => {
  const { today, wide, ready, setModelContext } = useAgent();
  const str = strings();
  const t = str.timesheet;
  const ISSUES = t.issues;
  const promptDay = resolveDay(props.date, today);
  const [monday, setMonday] = React.useState(weekStart(resolveDay(props.weekOf, today) ?? promptDay ?? today));
  const state = useServiceData(async (service, settings) => {
    const [me, entries, projects] = await Promise.all([service.me(), service.myEntries(monday, monday + 6), service.openProjects()]);
    return { me, entries, projects, settings };
  }, [monday]);
  const [lines, setLines] = React.useState<DraftLine[]>([]);
  const [nodes, setNodes] = React.useState<Record<string, Choice[]>>({});
  const [submitExisting, setSubmitExisting] = React.useState(true);
  const [step, setStep] = React.useState<Step>('edit');
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<Error | undefined>();
  const [receipt, setReceipt] = React.useState<{ created: number; submitted: number; submittedNow: boolean }>();
  const prefilled = React.useRef(false);

  const loadNodes = React.useCallback(async (projectId: string): Promise<Choice[]> => {
    if (nodes[projectId]) return nodes[projectId];
    const { service } = await ready;
    const list = await service.projectNodes(projectId);
    setNodes(n => ({ ...n, [projectId]: list }));
    return list;
  }, [nodes, ready]);

  // Prompt values become one editable draft line, once.
  React.useEffect(() => {
    if (!state.data || prefilled.current) return;
    prefilled.current = true;
    if (props.project === undefined && props.hours === undefined) return;
    const project = matchChoice(state.data.projects, props.project);
    const line: DraftLine = {
      key: newKey(), projectId: project?.id, day: promptDay ?? today, hours: props.hours !== undefined ? String(props.hours) : '', notes: props.notes,
    };
    setLines([line]);
    if (project) {
      loadNodes(project.id).then(list => {
        const node = matchChoice(list, props.wbsNode);
        if (node) setLines(ls => ls.map(l => (l.key === line.key ? { ...l, nodeId: node.id } : l)));
      }).catch(() => undefined);
    }
  }, [state.data]);

  const sheet = state.data ? buildTimesheet(state.data.entries, monday) : undefined;
  const plan = state.data ? planSubmission(lines, state.data.entries, !!state.data.me.resourceId, submitExisting) : undefined;
  const lineIssues = (key: string): DraftIssue[] => plan?.issues.filter(i => i.key === key) || [];
  const weekIssues = plan?.issues.filter(i => !i.key) || [];
  const days = Array.from({ length: 7 }, (_, i) => monday + i);
  const projectName = (id?: string): string => state.data?.projects.filter(p => p.id === id)[0]?.name || '–';
  const nodeName = (projectId?: string, id?: string): string => (projectId && id ? nodes[projectId]?.filter(n => n.id === id)[0]?.name : undefined) || '';

  React.useEffect(() => {
    if (!sheet || !plan) return;
    setModelContext(`Timesheet of the week of ${shortDate(monday)}: ${sheet.total} h recorded (`
      + sheet.rows.map(r => `${r.projectName}${r.nodeName ? ' / ' + r.nodeName : ''} ${r.total} h`).join(', ') + `). `
      + `Draft lines not yet saved: ${plan.creates.map(c => `${projectName(c.projectId)} ${shortDate(c.day)} ${c.hours} h`).join(', ') || 'none'}. `
      + `Step: ${step}. Nothing is saved or submitted until the user selects Confirm.`);
  }, [state.data, lines, step]);

  const update = (key: string, patch: Partial<DraftLine>): void => setLines(ls => ls.map(l => (l.key === key ? { ...l, ...patch } : l)));
  const addLine = (): void => setLines(ls => [...ls, { key: newKey(), day: today >= monday && today < monday + 7 ? today : monday, hours: '' }]);

  const confirm = async (submit: boolean): Promise<void> => {
    if (!plan || !canConfirm(plan)) return;
    setBusy(true);
    setError(undefined);
    let created = 0;
    try {
      const { service } = await ready;
      const ids: string[] = [];
      for (const c of plan.creates) {
        ids.push(await service.createEntry(c.projectId, c.nodeId, c.day, c.hours, c.notes));
        created++;
      }
      const toSubmit = submit ? [...ids, ...plan.existingToSubmit] : [];
      const submitted = toSubmit.length ? await service.submitEntries(toSubmit) : 0;
      setReceipt({ created, submitted, submittedNow: submit });
      setLines([]);
      setStep('done');
      state.reload();
    } catch (e) {
      setError(e as Error);
      if (created) { setLines(ls => ls.slice(created)); state.reload(); }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell eyebrow={t.eyebrow} title={str.intents.SubmitTimesheet.title} subtitle={`${str.common.weekOf(shortDate(monday))}${state.data?.me.resourceName ? ' · ' + state.data.me.resourceName : ''}`}
      onRefresh={step === 'review' ? undefined : state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {error && <ErrorBar error={error} />}
      {state.loading && !state.data && <Loading />}
      {step === 'done' && receipt && (
        <Info intent="success" title={receipt.submittedNow ? t.savedSubmitted : t.savedDraft}>
          {t.receipt(receipt.created, receipt.submittedNow ? receipt.submitted : undefined)}
          {receipt.submittedNow ? t.receiptSubmitted : t.receiptDraft}
        </Info>
      )}
      {state.data && sheet && plan && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Button size="small" icon={<ChevronLeft16Regular />} aria-label={t.previousWeek} disabled={step === 'review'} onClick={() => setMonday(m => m - 7)} />
            <Text weight="semibold">{shortDate(monday)} – {shortDate(monday + 6)}</Text>
            <Button size="small" icon={<ChevronRight16Regular />} aria-label={t.nextWeek} disabled={step === 'review'} onClick={() => setMonday(m => m + 7)} />
          </div>
          <KpiGrid>
            <Kpi label={t.recorded} value={hours(sheet.total)} note={t.expected(hours(state.data.me.weeklyHours))}
              tone={sheet.total < state.data.me.weeklyHours ? 'warning' : 'success'} />
            <Kpi label={t.toSubmit} value={String(plan.existingToSubmit.length || state.data.entries.filter(e => e.status === STATUS.draft || e.status === STATUS.rejected).length)}
              note={t.toSubmitNote} />
            <Kpi label={t.newLines} value={String(plan.creates.length)} note={hours(plan.creates.reduce((s, c) => s + c.hours, 0))} />
          </KpiGrid>
          {sheet.rows.length > 0 && (
            <Table size="small" aria-label={t.table}>
              <TableHeader>
                <TableRow>
                  <TableHeaderCell>{t.projectWbs}</TableHeaderCell>
                  {(wide ? days : []).map(d => <TableHeaderCell key={d} style={{ width: 64 }}>{weekday(d)}</TableHeaderCell>)}
                  <TableHeaderCell style={{ width: 70 }}>{t.total}</TableHeaderCell>
                  <TableHeaderCell style={{ width: 100 }}>{t.status}</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sheet.rows.map(r => {
                  const statuses = Array.from(new Set(r.cells.flatMap(c => c.entries.map(e => e.status))));
                  return (
                    <TableRow key={r.key}>
                      <TableCell>{r.projectName}{r.nodeName ? <Text size={200}> · {r.nodeName}</Text> : null}</TableCell>
                      {(wide ? r.cells : []).map((c, i) => <TableCell key={i}>{c.hours ? c.hours : ''}</TableCell>)}
                      <TableCell>{hours(r.total)}</TableCell>
                      <TableCell>{statuses.map(s => <Badge key={s} size="small" appearance="tint" color={STATUS_COLOR[s] || 'informative'}>{timeStatusLabel(s) || s}</Badge>)}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
          {step !== 'review' && (
            <>
              {lines.map(l => (
                <div key={l.key} style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'flex-start' }}>
                  <Field label={t.project} style={{ minWidth: 180, flexGrow: 2 }} validationMessage={lineIssues(l.key).filter(i => i.code === 'noProject').map(i => ISSUES[i.code])[0]}>
                    <Dropdown value={projectName(l.projectId) === '–' ? '' : projectName(l.projectId)} selectedOptions={l.projectId ? [l.projectId] : []}
                      placeholder={t.chooseProject} onOptionSelect={(_, d) => { update(l.key, { projectId: d.optionValue, nodeId: undefined }); if (d.optionValue) loadNodes(d.optionValue).catch(() => undefined); }}>
                      {state.data!.projects.map(p => <Option key={p.id} value={p.id}>{p.name}</Option>)}
                    </Dropdown>
                  </Field>
                  <Field label={t.wbsNode} style={{ minWidth: 150, flexGrow: 1 }}>
                    <Dropdown value={nodeName(l.projectId, l.nodeId)} selectedOptions={l.nodeId ? [l.nodeId] : []} disabled={!l.projectId}
                      placeholder={t.optional} onOptionSelect={(_, d) => update(l.key, { nodeId: d.optionValue })}>
                      {(l.projectId ? nodes[l.projectId] || [] : []).map(n => <Option key={n.id} value={n.id}>{n.name}</Option>)}
                    </Dropdown>
                  </Field>
                  <Field label={t.day} style={{ width: 120, flexShrink: 0 }}>
                    <Dropdown value={weekday(l.day)} selectedOptions={[String(l.day)]} onOptionSelect={(_, d) => update(l.key, { day: Number(d.optionValue) })}>
                      {(days.indexOf(l.day) >= 0 ? days : [l.day, ...days]).map(d => <Option key={d} value={String(d)} text={weekday(d)}>{weekday(d)}</Option>)}
                    </Dropdown>
                  </Field>
                  <Field label={t.hours} style={{ width: 96, flexShrink: 0 }} validationMessage={lineIssues(l.key).filter(i => i.code !== 'noProject').map(i => ISSUES[i.code])[0]}>
                    <Input value={l.hours} inputMode="decimal" style={FILL} input={{ style: FILL }} onChange={(_, d) => update(l.key, { hours: d.value })} />
                  </Field>
                  <Field label={t.notes} style={{ minWidth: 140, flexGrow: 2 }}>
                    <Input value={l.notes || ''} style={FILL} input={{ style: FILL }} onChange={(_, d) => update(l.key, { notes: d.value })} />
                  </Field>
                  <Button appearance="subtle" icon={<Delete16Regular />} style={{ marginTop: LABEL_HEIGHT }} aria-label={t.removeLine} onClick={() => setLines(ls => ls.filter(x => x.key !== l.key))} />
                </div>
              ))}
              <Footer>
                <Button size="small" icon={<Add16Regular />} onClick={addLine}>{t.addHours}</Button>
              </Footer>
              <Checkbox checked={submitExisting} onChange={(_, d) => setSubmitExisting(!!d.checked)}
                label={t.submitExisting} />
              {weekIssues.filter(i => i.code !== 'nothingToDo' || lines.length > 0).map((i, n) => (
                <Info key={n} intent={i.severity === 'error' ? 'error' : 'warning'}>{ISSUES[i.code]}{i.day !== undefined ? ` ${weekday(i.day)}.` : ''}</Info>
              ))}
              <Footer>
                <Button appearance="primary" disabled={!canConfirm(plan)} onClick={() => { setStep('review'); setReceipt(undefined); }}>{t.review}</Button>
                <OpenInApp url={listUrl(state.data.settings, 'op365_timeentry')} label={t.openList} />
              </Footer>
            </>
          )}
          {step === 'review' && (
            <>
              <Info title={t.reviewTitle}>
                {t.reviewText(plan.creates.length, hours(plan.creates.reduce((s, c) => s + c.hours, 0)), submitExisting ? plan.existingToSubmit.length : 0)}
              </Info>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {plan.creates.map((c, i) => (
                  <li key={i}><Text size={200}>{weekday(c.day)}: {projectName(c.projectId)}{c.nodeId ? ' · ' + nodeName(c.projectId, c.nodeId) : ''} · {hours(c.hours)}{c.notes ? ` · ${c.notes}` : ''}</Text></li>
                ))}
              </ul>
              {weekIssues.filter(i => i.severity === 'warning').map((i, n) => <Info key={n} intent="warning">{ISSUES[i.code]} {i.day !== undefined ? weekday(i.day) : ''}.</Info>)}
              <Footer>
                <Button appearance="primary" disabled={busy} onClick={() => { confirm(true).catch(() => undefined); }}>{busy ? str.common.saving : t.confirmSubmit}</Button>
                <Button disabled={busy || !plan.creates.length} onClick={() => { confirm(false).catch(() => undefined); }}>{t.saveDraft}</Button>
                <Button disabled={busy} onClick={() => setStep('edit')}>{str.common.back}</Button>
              </Footer>
            </>
          )}
        </>
      )}
    </Shell>
  );
};
