import * as React from 'react';
import { Badge, Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text } from '@fluentui/react-components';

import { useAgent, useServiceData } from '../AgentContext';
import { BudgetMeter, ErrorBar, FollowUp, Footer, HealthBadge, Info, Kpi, KpiGrid, Loading, OpenInApp, Section, Shell, ToneText } from '../kit';
import { date, hours, money, pct } from '../format';
import { projectStatusLabel } from '../labels';
import { ProjectGate } from './ProjectGate';
import { projectHealth, type ProjectFigures } from '../../logic/portfolio';
import { projectPhases } from '../../logic/project';
import { promptFor } from '../../intents';
import { recordUrl } from '../../settings';
import { EN, strings } from '../../i18n';

const Detail: React.FC<{ project: ProjectFigures }> = ({ project }) => {
  const { today, wide, setModelContext } = useAgent();
  const s = strings();
  const t = s.project;
  const state = useServiceData(async (service, settings) => ({ ...(await service.projectDetail(project.id)), settings }), [project.id]);
  const d = state.data;
  const health = d ? projectHealth(d.project, today) : undefined;
  const phases = React.useMemo(() => (d ? projectPhases(d.nodes, d.actuals, today, d.baseline?.nodes) : []), [d, today]);
  React.useEffect(() => {
    if (!d || !health) return;
    const p = d.project;
    setModelContext(`Project ${p.code} ${p.name} (${projectStatusLabel(p.status, EN) || p.status}), customer ${p.customer || '-'}, manager ${p.manager || '-'}. `
      + `Health ${health.level}${health.reasons.length ? ': ' + health.reasons.map(r => EN.reasons[r]).join('; ') : ''}. `
      + `Progress ${p.progress}%. Contract ${p.contract}, budget ${p.budget}, actual ${p.actual}, committed ${p.committed}, remaining ${health.remaining}, `
      + `EAC ${Math.round(health.eac)}, margin ${Math.round(health.margin)}. Dates ${date(p.start)} - ${date(p.end)}. `
      + `Open purchase requests ${d.openRequests}, open orders ${d.openOrders}. Phases: `
      + phases.map(f => `${f.node.code} ${f.node.name} progress ${f.node.rollProgress}% budget ${f.node.totalBudget} actual ${f.actualCost}`
        + `${f.late ? ' LATE' : ''}${f.hoursOverrun ? ' HOURS OVERRUN' : ''}${f.slipDays ? ` slip ${f.slipDays} days` : ''}`).join('; '));
  }, [d]);

  const p = d?.project || project;
  const sym = d?.currencySymbol;
  return (
    <Shell eyebrow={t.eyebrow} title={`${p.code} ${p.name}`.trim()} subtitle={[p.customer, p.manager && t.pm(p.manager), projectStatusLabel(p.status)].filter(Boolean).join(' · ')}
      onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !d && <Loading />}
      {d && health && (
        <>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <HealthBadge level={health.level} />
            {health.reasons.map(r => <Badge key={r} appearance="outline" color="subtle">{s.reasons[r]}</Badge>)}
          </div>
          <KpiGrid>
            <Kpi label={t.progress} value={pct(p.progress / 100)} note={health.elapsed !== undefined ? t.elapsed(pct(health.elapsed)) : undefined} />
            <Kpi label={t.budget} value={money(p.budget, sym)} note={s.common.used(pct(health.budgetUsed))} tone={health.budgetUsed > 1 ? 'danger' : 'neutral'} />
            <Kpi label={t.actual} value={money(p.actual, sym)} note={hours(p.actualHours)} />
            <Kpi label={t.committed} value={money(p.committed, sym)} note={t.committedNote} />
            <Kpi label={t.remaining} value={money(health.remaining, sym)} tone={health.remaining < 0 ? 'danger' : 'neutral'} />
            <Kpi label={t.margin} value={money(health.margin, sym)} note={s.common.eac(money(health.eac, sym))} tone={health.margin < 0 ? 'danger' : 'neutral'} />
          </KpiGrid>
          <BudgetMeter budget={p.budget} actual={p.actual} committed={p.committed} />
          <Text size={200}>{date(p.start)} → {date(p.end)}{d.baseline ? ` · ${t.baseline(d.baseline.name)}` : ''}</Text>
          <Section title={t.phases}>
            {!phases.length && <Info>{t.noWbs}</Info>}
            {!!phases.length && (
              <Table size="small" aria-label={t.phases}>
                <TableHeader>
                  <TableRow>
                    <TableHeaderCell>{t.phase}</TableHeaderCell>
                    <TableHeaderCell style={{ width: 70 }}>{t.progress}</TableHeaderCell>
                    <TableHeaderCell>{t.budgetUsed}</TableHeaderCell>
                    {wide && <TableHeaderCell style={{ width: 110 }}>{t.hours}</TableHeaderCell>}
                    {wide && <TableHeaderCell style={{ width: 100 }}>{t.end}</TableHeaderCell>}
                    {wide && d.baseline && <TableHeaderCell style={{ width: 90 }}>{t.slip}</TableHeaderCell>}
                    <TableHeaderCell style={{ width: 120 }}>{t.flags}</TableHeaderCell>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {phases.map(f => (
                    <TableRow key={f.node.id}>
                      <TableCell><Text weight="semibold">{f.node.code}</Text> {f.node.name}</TableCell>
                      <TableCell>{pct(f.node.rollProgress / 100)}</TableCell>
                      <TableCell><BudgetMeter budget={f.node.totalBudget} actual={f.actualCost} /></TableCell>
                      {wide && <TableCell>{hours(f.actualHours)} / {hours(f.node.totalHours)}</TableCell>}
                      {wide && <TableCell>{date(f.node.rollEnd)}</TableCell>}
                      {wide && d.baseline && <TableCell><ToneText tone={(f.slipDays || 0) > 0 ? 'warning' : 'neutral'}>{f.slipDays ? `${f.slipDays > 0 ? '+' : ''}${s.common.days(f.slipDays)}` : '–'}</ToneText></TableCell>}
                      <TableCell>
                        {f.late && <Badge color="danger" appearance="tint">{t.late}</Badge>}{' '}
                        {f.hoursOverrun && <Badge color="warning" appearance="tint">{t.hoursOver}</Badge>}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Section>
          {(d.openRequests > 0 || d.openOrders > 0) && (
            <Info>{t.openPurchases(d.openRequests, d.openOrders)}</Info>
          )}
          <Footer>
            <OpenInApp url={recordUrl(d.settings, 'op365_project', p.id)} />
            <FollowUp prompt={promptFor('GetProjectBudget', p.code || p.name)}>{t.budgetDetail}</FollowUp>
            <FollowUp prompt={promptFor('GetProjectTimeline', p.code || p.name)}>{t.timeline}</FollowUp>
            {(d.openRequests > 0 || d.openOrders > 0) && <FollowUp prompt={s.prompts.projectPurchasing(p.code || p.name)}>{t.purchasing}</FollowUp>}
          </Footer>
        </>
      )}
    </Shell>
  );
};

export const ProjectHealthView: React.FC<{ project?: string }> = props => (
  <ProjectGate intent="GetProjectHealth" eyebrow={strings().project.eyebrow} title={strings().intents.GetProjectHealth.title} project={props.project}>
    {project => <Detail project={project} />}
  </ProjectGate>
);
