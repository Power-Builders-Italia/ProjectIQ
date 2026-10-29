import * as React from 'react';
import { Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text } from '@fluentui/react-components';

import { useAgent, useServiceData } from '../AgentContext';
import { BudgetMeter, ErrorBar, Footer, HealthBadge, Info, Kpi, KpiGrid, Loading, OpenInApp, Shell, ToneText } from '../kit';
import { money, pct, date } from '../format';
import { REASON_LABELS } from '../labels';
import { portfolioSummary, type HealthLevel } from '../../logic/portfolio';
import { promptFor } from '../../intents';
import { listUrl } from '../../settings';

export interface PortfolioHealthProps {
  health?: HealthLevel;
  customer?: string;
  manager?: string;
  includeClosed?: boolean;
}

const contains = (value: string | undefined, q: string | undefined): boolean =>
  !q || (value || '').toLowerCase().indexOf(q.trim().toLowerCase()) >= 0;

export const PortfolioHealthView: React.FC<PortfolioHealthProps> = props => {
  const { today, wide, followUp, setModelContext } = useAgent();
  const state = useServiceData(async (service, settings) => ({ ...(await service.projects(props.includeClosed)), settings }), [props.includeClosed]);
  const data = state.data;
  const summary = React.useMemo(() => {
    if (!data) return undefined;
    const filtered = data.projects.filter(p => contains(p.customer, props.customer) && contains(p.manager, props.manager));
    return portfolioSummary(filtered, today);
  }, [data, props.customer, props.manager, today]);
  const rows = summary ? summary.rows.filter(r => !props.health || r.health.level === props.health) : [];
  React.useEffect(() => {
    if (!summary) return;
    setModelContext(`ProjectIQ portfolio: ${summary.counts.offTrack} off track, ${summary.counts.atRisk} at risk, ${summary.counts.onTrack} on track. `
      + rows.slice(0, 40).map(r => `${r.code} ${r.name}: ${r.health.level}, progress ${r.progress}%, budget ${r.budget}, actual ${r.actual}, `
        + `committed ${r.committed}, EAC ${Math.round(r.health.eac)}, margin ${Math.round(r.health.margin)}`
        + (r.health.reasons.length ? ` (${r.health.reasons.map(x => REASON_LABELS[x]).join('; ')})` : '')).join('\n'));
  }, [summary, props.health]);

  const filters = [props.health && `health: ${props.health}`, props.customer && `customer: ${props.customer}`, props.manager && `manager: ${props.manager}`]
    .filter(Boolean).join(' · ');
  const sym = data?.currencySymbol;
  return (
    <Shell eyebrow="Portfolio" title="Portfolio health" subtitle={filters || 'Projects you can see in ProjectIQ'} onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !data && <Loading />}
      {summary && (
        <>
          <KpiGrid>
            <Kpi label="Off track" value={String(summary.counts.offTrack)} tone={summary.counts.offTrack ? 'danger' : 'neutral'} />
            <Kpi label="At risk" value={String(summary.counts.atRisk)} tone={summary.counts.atRisk ? 'warning' : 'neutral'} />
            <Kpi label="On track" value={String(summary.counts.onTrack)} tone="success" />
            <Kpi label="Contract value" value={money(summary.contract, sym, true)} />
            <Kpi label="Budget" value={money(summary.budget, sym, true)} note={`${pct(summary.budget ? (summary.actual + summary.committed) / summary.budget : 0)} used`} />
            <Kpi label="Margin at completion" value={money(summary.margin, sym, true)} tone={summary.margin < 0 ? 'danger' : 'neutral'}
              note={`EAC ${money(summary.eac, sym, true)}`} />
          </KpiGrid>
          {!rows.length && <Info>No project matches.</Info>}
          {!!rows.length && (
            <Table size="small" aria-label="Projects">
              <TableHeader>
                <TableRow>
                  <TableHeaderCell>Project</TableHeaderCell>
                  <TableHeaderCell style={{ width: 100 }}>Health</TableHeaderCell>
                  {wide && <TableHeaderCell>Customer</TableHeaderCell>}
                  {wide && <TableHeaderCell style={{ width: 100 }}>End</TableHeaderCell>}
                  <TableHeaderCell style={{ width: 70 }}>Progress</TableHeaderCell>
                  <TableHeaderCell>Budget used</TableHeaderCell>
                  <TableHeaderCell style={{ width: 110 }}>Margin</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.slice(0, wide ? 200 : 8).map(r => (
                  <TableRow key={r.id} onClick={() => followUp(promptFor('GetProjectHealth', r.code || r.name))} style={{ cursor: 'pointer' }}>
                    <TableCell>
                      <Text weight="semibold">{r.code}</Text> {r.name}
                      {wide && r.health.reasons.length > 0 && <div><Text size={200}>{r.health.reasons.map(x => REASON_LABELS[x]).join(' · ')}</Text></div>}
                    </TableCell>
                    <TableCell><HealthBadge level={r.health.level} /></TableCell>
                    {wide && <TableCell>{r.customer}</TableCell>}
                    {wide && <TableCell>{date(r.end)}</TableCell>}
                    <TableCell>{Math.round(r.progress)}%</TableCell>
                    <TableCell><BudgetMeter budget={r.budget} actual={r.actual} committed={r.committed} /></TableCell>
                    <TableCell><ToneText tone={r.health.margin < 0 ? 'danger' : 'neutral'}>{money(r.health.margin, sym, true)}</ToneText></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {!wide && rows.length > 8 && <Text size={200}>{rows.length - 8} more projects: expand to see them all.</Text>}
          <Footer><OpenInApp url={listUrl(data!.settings, 'op365_project')} label="Open projects in ProjectIQ" /></Footer>
        </>
      )}
    </Shell>
  );
};
