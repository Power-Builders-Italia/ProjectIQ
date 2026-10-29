import * as React from 'react';
import { Badge, Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text } from '@fluentui/react-components';

import { useAgent, useServiceData } from '../AgentContext';
import { BudgetMeter, ErrorBar, FollowUp, Footer, HealthBadge, Info, Kpi, KpiGrid, Loading, OpenInApp, Section, Shell, ToneText } from '../kit';
import { date, hours, money, pct } from '../format';
import { PROJECT_STATUS_LABELS, REASON_LABELS } from '../labels';
import { ProjectGate } from './ProjectGate';
import { projectHealth, type ProjectFigures } from '../../logic/portfolio';
import { projectPhases } from '../../logic/project';
import { promptFor } from '../../intents';
import { recordUrl } from '../../settings';

const Detail: React.FC<{ project: ProjectFigures }> = ({ project }) => {
  const { today, wide, setModelContext } = useAgent();
  const state = useServiceData(async (service, settings) => ({ ...(await service.projectDetail(project.id)), settings }), [project.id]);
  const d = state.data;
  const health = d ? projectHealth(d.project, today) : undefined;
  const phases = React.useMemo(() => (d ? projectPhases(d.nodes, d.actuals, today, d.baseline?.nodes) : []), [d, today]);
  React.useEffect(() => {
    if (!d || !health) return;
    const p = d.project;
    setModelContext(`Project ${p.code} ${p.name} (${PROJECT_STATUS_LABELS[p.status] || p.status}), customer ${p.customer || '-'}, manager ${p.manager || '-'}. `
      + `Health ${health.level}${health.reasons.length ? ': ' + health.reasons.map(r => REASON_LABELS[r]).join('; ') : ''}. `
      + `Progress ${p.progress}%. Contract ${p.contract}, budget ${p.budget}, actual ${p.actual}, committed ${p.committed}, remaining ${health.remaining}, `
      + `EAC ${Math.round(health.eac)}, margin ${Math.round(health.margin)}. Dates ${date(p.start)} - ${date(p.end)}. `
      + `Open purchase requests ${d.openRequests}, open orders ${d.openOrders}. Phases: `
      + phases.map(f => `${f.node.code} ${f.node.name} progress ${f.node.rollProgress}% budget ${f.node.totalBudget} actual ${f.actualCost}`
        + `${f.late ? ' LATE' : ''}${f.hoursOverrun ? ' HOURS OVERRUN' : ''}${f.slipDays ? ` slip ${f.slipDays} days` : ''}`).join('; '));
  }, [d]);

  const p = d?.project || project;
  const sym = d?.currencySymbol;
  return (
    <Shell eyebrow="Project" title={`${p.code} ${p.name}`.trim()} subtitle={[p.customer, p.manager && `PM ${p.manager}`, PROJECT_STATUS_LABELS[p.status]].filter(Boolean).join(' · ')}
      onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !d && <Loading />}
      {d && health && (
        <>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <HealthBadge level={health.level} />
            {health.reasons.map(r => <Badge key={r} appearance="outline" color="subtle">{REASON_LABELS[r]}</Badge>)}
          </div>
          <KpiGrid>
            <Kpi label="Progress" value={`${Math.round(p.progress)}%`} note={health.elapsed !== undefined ? `${pct(health.elapsed)} of time elapsed` : undefined} />
            <Kpi label="Budget" value={money(p.budget, sym)} note={`${pct(health.budgetUsed)} used`} tone={health.budgetUsed > 1 ? 'danger' : 'neutral'} />
            <Kpi label="Actual cost" value={money(p.actual, sym)} note={hours(p.actualHours)} />
            <Kpi label="Committed" value={money(p.committed, sym)} note="Open orders not received" />
            <Kpi label="Remaining" value={money(health.remaining, sym)} tone={health.remaining < 0 ? 'danger' : 'neutral'} />
            <Kpi label="Margin at completion" value={money(health.margin, sym)} note={`EAC ${money(health.eac, sym)}`} tone={health.margin < 0 ? 'danger' : 'neutral'} />
          </KpiGrid>
          <BudgetMeter budget={p.budget} actual={p.actual} committed={p.committed} />
          <Text size={200}>{date(p.start)} → {date(p.end)}{d.baseline ? ` · reference baseline "${d.baseline.name}"` : ''}</Text>
          <Section title="WBS phases">
            {!phases.length && <Info>The project has no WBS yet.</Info>}
            {!!phases.length && (
              <Table size="small" aria-label="WBS phases">
                <TableHeader>
                  <TableRow>
                    <TableHeaderCell>Phase</TableHeaderCell>
                    <TableHeaderCell style={{ width: 70 }}>Progress</TableHeaderCell>
                    <TableHeaderCell>Budget used</TableHeaderCell>
                    {wide && <TableHeaderCell style={{ width: 110 }}>Hours</TableHeaderCell>}
                    {wide && <TableHeaderCell style={{ width: 100 }}>End</TableHeaderCell>}
                    {wide && d.baseline && <TableHeaderCell style={{ width: 90 }}>Slip</TableHeaderCell>}
                    <TableHeaderCell style={{ width: 120 }}>Flags</TableHeaderCell>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {phases.map(f => (
                    <TableRow key={f.node.id}>
                      <TableCell><Text weight="semibold">{f.node.code}</Text> {f.node.name}</TableCell>
                      <TableCell>{Math.round(f.node.rollProgress)}%</TableCell>
                      <TableCell><BudgetMeter budget={f.node.totalBudget} actual={f.actualCost} /></TableCell>
                      {wide && <TableCell>{hours(f.actualHours)} / {hours(f.node.totalHours)}</TableCell>}
                      {wide && <TableCell>{date(f.node.rollEnd)}</TableCell>}
                      {wide && d.baseline && <TableCell><ToneText tone={(f.slipDays || 0) > 0 ? 'warning' : 'neutral'}>{f.slipDays ? `${f.slipDays > 0 ? '+' : ''}${f.slipDays} d` : '–'}</ToneText></TableCell>}
                      <TableCell>
                        {f.late && <Badge color="danger" appearance="tint">Late</Badge>}{' '}
                        {f.hoursOverrun && <Badge color="warning" appearance="tint">Hours over</Badge>}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Section>
          {(d.openRequests > 0 || d.openOrders > 0) && (
            <Info>{d.openRequests} purchase requests waiting for approval · {d.openOrders} purchase orders not yet received.</Info>
          )}
          <Footer>
            <OpenInApp url={recordUrl(d.settings, 'op365_project', p.id)} />
            <FollowUp prompt={promptFor('GetProjectBudget', p.code || p.name)}>Budget detail</FollowUp>
            <FollowUp prompt={promptFor('GetProjectTimeline', p.code || p.name)}>Timeline</FollowUp>
            {(d.openRequests > 0 || d.openOrders > 0) && <FollowUp prompt={`What is the purchasing status of project ${p.code || p.name}?`}>Purchasing</FollowUp>}
          </Footer>
        </>
      )}
    </Shell>
  );
};

export const ProjectHealthView: React.FC<{ project?: string }> = props => (
  <ProjectGate intent="GetProjectHealth" eyebrow="Project" title="Project health" project={props.project}>
    {project => <Detail project={project} />}
  </ProjectGate>
);
