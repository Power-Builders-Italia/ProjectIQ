import * as React from 'react';
import { Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text } from '@fluentui/react-components';

import { useAgent, useServiceData } from '../AgentContext';
import { BudgetMeter, ErrorBar, Footer, HealthBadge, Info, Kpi, KpiGrid, Loading, OpenInApp, Shell, ToneText } from '../kit';
import { money, pct, date } from '../format';
import { portfolioSummary, type HealthLevel } from '../../logic/portfolio';
import { promptFor } from '../../intents';
import { listUrl } from '../../settings';
import { EN, strings } from '../../i18n';

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
  const s = strings();
  const t = s.portfolio;
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
        + (r.health.reasons.length ? ` (${r.health.reasons.map(x => EN.reasons[x]).join('; ')})` : '')).join('\n'));
  }, [summary, props.health]);

  const filters = [props.health && t.filterHealth(s.health[props.health]), props.customer && t.filterCustomer(props.customer), props.manager && t.filterManager(props.manager)]
    .filter(Boolean).join(' · ');
  const sym = data?.currencySymbol;
  return (
    <Shell eyebrow={t.eyebrow} title={s.intents.GetPortfolioHealth.title} subtitle={filters || t.subtitle} onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !data && <Loading />}
      {summary && (
        <>
          <KpiGrid>
            <Kpi label={s.health.offTrack} value={String(summary.counts.offTrack)} tone={summary.counts.offTrack ? 'danger' : 'neutral'} />
            <Kpi label={s.health.atRisk} value={String(summary.counts.atRisk)} tone={summary.counts.atRisk ? 'warning' : 'neutral'} />
            <Kpi label={s.health.onTrack} value={String(summary.counts.onTrack)} tone="success" />
            <Kpi label={t.contract} value={money(summary.contract, sym, true)} />
            <Kpi label={t.budget} value={money(summary.budget, sym, true)} note={s.common.used(pct(summary.budget ? (summary.actual + summary.committed) / summary.budget : 0))} />
            <Kpi label={t.margin} value={money(summary.margin, sym, true)} tone={summary.margin < 0 ? 'danger' : 'neutral'}
              note={s.common.eac(money(summary.eac, sym, true))} />
          </KpiGrid>
          {!rows.length && <Info>{t.noMatch}</Info>}
          {!!rows.length && (
            <Table size="small" aria-label={t.projects}>
              <TableHeader>
                <TableRow>
                  <TableHeaderCell>{t.project}</TableHeaderCell>
                  <TableHeaderCell style={{ width: 100 }}>{t.health}</TableHeaderCell>
                  {wide && <TableHeaderCell>{t.customer}</TableHeaderCell>}
                  {wide && <TableHeaderCell style={{ width: 100 }}>{t.end}</TableHeaderCell>}
                  <TableHeaderCell style={{ width: 70 }}>{t.progress}</TableHeaderCell>
                  <TableHeaderCell>{t.budgetUsed}</TableHeaderCell>
                  <TableHeaderCell style={{ width: 110 }}>{t.marginColumn}</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.slice(0, wide ? 200 : 8).map(r => (
                  <TableRow key={r.id} onClick={() => followUp(promptFor('GetProjectHealth', r.code || r.name))} style={{ cursor: 'pointer' }}>
                    <TableCell>
                      <Text weight="semibold">{r.code}</Text> {r.name}
                      {wide && r.health.reasons.length > 0 && <div><Text size={200}>{r.health.reasons.map(x => s.reasons[x]).join(' · ')}</Text></div>}
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
          {!wide && rows.length > 8 && <Text size={200}>{t.more(rows.length - 8)}</Text>}
          <Footer><OpenInApp url={listUrl(data!.settings, 'op365_project')} label={t.openList} /></Footer>
        </>
      )}
    </Shell>
  );
};
