import * as React from 'react';
import {
  Badge, Button, Checkbox, Field, Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text, Textarea,
} from '@fluentui/react-components';
import { Checkmark16Regular, Dismiss16Regular } from '@fluentui/react-icons';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, Footer, Info, Kpi, KpiGrid, Loading, OpenInApp, Shell } from '../kit';
import { date, hours, shortDate } from '../format';
import { approvalQueue, idsToDecide, type FlaggedGroup } from '../../logic/approvals';
import { listUrl } from '../../settings';

export interface TimeApprovalsProps { project?: string; resource?: string; }

type Step = { kind: 'select' } | { kind: 'review'; approve: boolean } | { kind: 'done'; approve: boolean; count: number };

const contains = (v: string, q?: string): boolean => !q || v.toLowerCase().indexOf(q.trim().toLowerCase()) >= 0;

export const TimeApprovalsView: React.FC<TimeApprovalsProps> = props => {
  const { today, wide, ready, setModelContext } = useAgent();
  const state = useServiceData(async (service, settings) => ({ entries: await service.pendingTime(), settings }), []);
  const groups = React.useMemo(() => (state.data
    ? approvalQueue(state.data.entries.filter(e => contains(e.projectName, props.project) && contains(e.resourceName, props.resource)), today)
    : []), [state.data, props.project, props.resource, today]);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [step, setStep] = React.useState<Step>({ kind: 'select' });
  const [note, setNote] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<Error | undefined>();

  React.useEffect(() => {
    if (!state.data) return;
    setModelContext(`Hours waiting for approval: ` + groups.map(g => `${g.resourceName}, week of ${shortDate(g.weekStart)}: ${g.hours} h `
      + `(${g.projects.map(p => `${p.name} ${p.hours} h`).join(', ')})${g.flags.stale ? ', submitted more than 7 days ago' : ''}`
      + `${g.flags.longDays.length ? ', days over 10 h' : ''}`).join('\n') + `\nCurrent step: ${step.kind}. Nothing is approved until the user selects Confirm.`);
  }, [groups, step.kind]);

  const chosen: FlaggedGroup[] = selected.size ? groups.filter(g => selected.has(g.key)) : groups;
  const chosenHours = chosen.reduce((s, g) => s + g.hours, 0);
  const toggle = (key: string): void => setSelected(prev => {
    const next = new Set(prev);
    if (next.has(key)) next.delete(key); else next.add(key);
    return next;
  });
  const confirm = async (approve: boolean): Promise<void> => {
    setBusy(true);
    setError(undefined);
    try {
      const { service } = await ready;
      const count = await service.decideEntries(idsToDecide(groups, selected), approve, approve ? undefined : note.trim());
      setStep({ kind: 'done', approve, count });
      setSelected(new Set());
      setNote('');
      state.reload();
    } catch (e) {
      setError(e as Error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell eyebrow="Approvals" title="Approve hours" subtitle={[props.project, props.resource].filter(Boolean).join(' · ') || 'Submitted hours of the projects you manage'}
      onRefresh={step.kind === 'review' ? undefined : state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {error && <ErrorBar error={error} />}
      {state.loading && !state.data && <Loading />}
      {step.kind === 'done' && (
        <Info intent="success" title={step.approve ? 'Hours approved' : 'Hours rejected'}>
          {step.count} time entries {step.approve ? 'approved' : 'rejected'} in ProjectIQ. The people concerned get an in-app notification.
        </Info>
      )}
      {state.data && step.kind !== 'review' && (
        <>
          <KpiGrid>
            <Kpi label="Entries to approve" value={String(groups.reduce((n, g) => n + g.entries.length, 0))} />
            <Kpi label="Hours" value={hours(groups.reduce((n, g) => n + g.hours, 0))} />
            <Kpi label="Waiting > 7 days" value={String(groups.filter(g => g.flags.stale).length)} tone={groups.some(g => g.flags.stale) ? 'warning' : 'neutral'} />
          </KpiGrid>
          {!groups.length && <Info>Nothing to approve. When time approval is off in the settings, hours are approved on submit.</Info>}
          {!!groups.length && (
            <Table size="small" aria-label="Hours to approve">
              <TableHeader>
                <TableRow>
                  <TableHeaderCell style={{ width: 36 }} />
                  <TableHeaderCell>Person · week</TableHeaderCell>
                  <TableHeaderCell style={{ width: 80 }}>Hours</TableHeaderCell>
                  {wide && <TableHeaderCell>Projects</TableHeaderCell>}
                  <TableHeaderCell style={{ width: 140 }}>Flags</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {groups.slice(0, wide ? 500 : 10).map(g => (
                  <TableRow key={g.key}>
                    <TableCell><Checkbox checked={selected.has(g.key)} onChange={() => toggle(g.key)} aria-label={`Select ${g.resourceName}`} /></TableCell>
                    <TableCell>
                      <Text weight="semibold">{g.resourceName}</Text> · {shortDate(g.weekStart)}
                      {!wide && <div><Text size={200}>{g.projects.map(p => p.name).join(', ')}</Text></div>}
                    </TableCell>
                    <TableCell>{hours(g.hours)}</TableCell>
                    {wide && <TableCell>{g.projects.map(p => `${p.name} ${hours(p.hours)}`).join(' · ')}</TableCell>}
                    <TableCell>
                      {g.flags.stale && <Badge color="warning" appearance="tint">Since {date(g.oldestSubmission)}</Badge>}{' '}
                      {g.flags.longDays.length > 0 && <Badge color="danger" appearance="tint">{g.flags.longDays.length} days &gt; 10 h</Badge>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {!!groups.length && (
            <Footer>
              <Button appearance="primary" icon={<Checkmark16Regular />} onClick={() => setStep({ kind: 'review', approve: true })}>
                {selected.size ? 'Approve selected…' : 'Approve all…'}
              </Button>
              <Button icon={<Dismiss16Regular />} onClick={() => setStep({ kind: 'review', approve: false })}>
                {selected.size ? 'Reject selected…' : 'Reject all…'}
              </Button>
              <OpenInApp url={listUrl(state.data.settings, 'op365_timeentry')} label="Open Approvals in ProjectIQ" />
            </Footer>
          )}
        </>
      )}
      {state.data && step.kind === 'review' && (
        <>
          <Info intent={step.approve ? 'info' : 'warning'} title={step.approve ? 'Review the approval' : 'Review the rejection'}>
            You are about to {step.approve ? 'approve' : 'reject'} {chosen.reduce((n, g) => n + g.entries.length, 0)} time entries,
            {' '}{hours(chosenHours)} of {new Set(chosen.map(g => g.resourceId)).size} people. Approved hours become actual cost of the projects.
          </Info>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {chosen.slice(0, 12).map(g => <li key={g.key}><Text size={200}>{g.resourceName}, week of {shortDate(g.weekStart)}: {hours(g.hours)}</Text></li>)}
            {chosen.length > 12 && <li><Text size={200}>…and {chosen.length - 12} more</Text></li>}
          </ul>
          {!step.approve && (
            <Field label="Note for the people (required to reject)" required>
              <Textarea value={note} onChange={(_, d) => setNote(d.value)} resize="vertical" />
            </Field>
          )}
          <Footer>
            <Button appearance="primary" disabled={busy || (!step.approve && !note.trim())} onClick={() => { confirm(step.approve).catch(() => undefined); }}>
              {busy ? 'Saving…' : step.approve ? 'Confirm approval' : 'Confirm rejection'}
            </Button>
            <Button disabled={busy} onClick={() => setStep({ kind: 'select' })}>Back</Button>
          </Footer>
        </>
      )}
    </Shell>
  );
};
