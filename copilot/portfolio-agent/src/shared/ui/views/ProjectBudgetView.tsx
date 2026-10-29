import * as React from 'react';
import { Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text, tokens } from '@fluentui/react-components';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, FollowUp, Footer, Kpi, KpiGrid, Loading, OpenInApp, Shell, ToneText } from '../kit';
import { hours, money, pct } from '../format';
import { ProjectGate } from './ProjectGate';
import { buildTree } from '../../projectiq/wbs';
import { costSummary, type CostLine } from '../../projectiq/cost';
import type { ProjectFigures } from '../../logic/portfolio';
import { promptFor } from '../../intents';
import { recordUrl } from '../../settings';
import { strings } from '../../i18n';

/** Horizontal bars: budget (outline) and actual (filled) for each WBS branch. */
const BudgetBars: React.FC<{ lines: CostLine[]; symbol?: string }> = ({ lines, symbol }) => {
  const t = strings().budget;
  const max = Math.max(1, ...lines.map(l => Math.max(l.budget, l.actual)));
  const rowH = 26;
  const labelW = 150;
  return (
    <svg width="100%" height={lines.length * rowH + 4} role="img" aria-label={t.chart}
      viewBox={`0 0 600 ${lines.length * rowH + 4}`} preserveAspectRatio="xMinYMin meet">
      {lines.map((l, i) => {
        const y = i * rowH + 4;
        const w = 600 - labelW - 90;
        return (
          <g key={l.id || i}>
            <text x={0} y={y + 13} fontSize={11} fill={tokens.colorNeutralForeground2}>{(l.code ? l.code + ' ' : '') + (l.name || t.notOnWbs)}</text>
            <rect x={labelW} y={y + 2} width={l.budget / max * w} height={16} rx={3} fill="none" stroke={tokens.colorNeutralStroke1} />
            <rect x={labelW} y={y + 5} width={l.actual / max * w} height={10} rx={2}
              fill={l.actual > l.budget ? tokens.colorPaletteRedBackground3 : tokens.colorBrandBackground} />
            <text x={labelW + w + 6} y={y + 14} fontSize={11} fill={tokens.colorNeutralForeground2}>{money(l.actual, symbol, true)}</text>
          </g>
        );
      })}
    </svg>
  );
};

const Detail: React.FC<{ project: ProjectFigures }> = ({ project }) => {
  const { wide, setModelContext } = useAgent();
  const s = strings();
  const t = s.budget;
  const state = useServiceData(async (service, settings) => {
    const [detail, totals] = await Promise.all([service.projectDetail(project.id), service.labourAndMaterials(project.id)]);
    return { detail, totals, settings };
  }, [project.id]);
  const summary = React.useMemo(() => {
    if (!state.data) return undefined;
    const { detail, totals } = state.data;
    const nodeCost = [...detail.actuals.values()].reduce((t, a) => t + a.actualCost, 0);
    const nodeHours = [...detail.actuals.values()].reduce((t, a) => t + a.actualHours, 0);
    return costSummary(buildTree(detail.nodes), detail.actuals, {
      contract: detail.project.contract, labour: totals.labour, materials: totals.materials, progressPct: detail.project.progress,
      unassignedCost: Math.max(0, detail.project.actual - nodeCost), unassignedHours: Math.max(0, detail.project.actualHours - nodeHours),
    });
  }, [state.data]);
  React.useEffect(() => {
    if (!summary) return;
    setModelContext(`Budget of project ${project.code} ${project.name}: budget ${summary.budget}, actual ${summary.actual} (labour ${summary.labour}, `
      + `materials ${summary.materials}), contract ${summary.contract}, EAC ${Math.round(summary.eac)}, margin ${Math.round(summary.margin)}, `
      + `committed ${state.data?.detail.project.committed}. By WBS branch: `
      + summary.lines.map(l => `${l.code} ${l.name || 'not on the WBS'} budget ${l.budget} actual ${l.actual} variance ${l.variance}`).join('; '));
  }, [summary]);
  const sym = state.data?.detail.currencySymbol;
  return (
    <Shell eyebrow={t.eyebrow} title={`${project.code} ${project.name}`.trim()} subtitle={t.subtitle} onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !summary && <Loading />}
      {summary && state.data && (
        <>
          <KpiGrid>
            <Kpi label={t.budget} value={money(summary.budget, sym)} />
            <Kpi label={t.actual} value={money(summary.actual, sym)} note={t.ofBudget(pct(summary.budget ? summary.actual / summary.budget : 0))}
              tone={summary.actual > summary.budget ? 'danger' : 'neutral'} />
            <Kpi label={t.labour} value={money(summary.labour, sym)} note={t.labourNote} />
            <Kpi label={t.materials} value={money(summary.materials, sym)} />
            <Kpi label={t.committed} value={money(state.data.detail.project.committed, sym)} />
            <Kpi label={t.eac} value={money(summary.eac, sym)} note={t.marginNote(money(summary.margin, sym))}
              tone={summary.margin < 0 ? 'danger' : 'neutral'} />
          </KpiGrid>
          {summary.lines.length > 0 && <BudgetBars lines={summary.lines} symbol={sym} />}
          {wide && summary.lines.length > 0 && (
            <Table size="small" aria-label={t.table}>
              <TableHeader>
                <TableRow>
                  <TableHeaderCell>{t.branch}</TableHeaderCell>
                  <TableHeaderCell>{t.budget}</TableHeaderCell>
                  <TableHeaderCell>{t.actualColumn}</TableHeaderCell>
                  <TableHeaderCell>{t.variance}</TableHeaderCell>
                  <TableHeaderCell>{t.hours}</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.lines.map((l, i) => (
                  <TableRow key={l.id || i}>
                    <TableCell><Text weight="semibold">{l.code}</Text> {l.name || t.notOnWbs}</TableCell>
                    <TableCell>{money(l.budget, sym)}</TableCell>
                    <TableCell>{money(l.actual, sym)}</TableCell>
                    <TableCell><ToneText tone={l.variance > 0 ? 'danger' : 'success'}>{money(l.variance, sym)}</ToneText></TableCell>
                    <TableCell>{hours(l.actualHours)} / {hours(l.budgetHours)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <Text size={200}>{t.note}</Text>
          <Footer>
            <OpenInApp url={recordUrl(state.data.settings, 'op365_project', project.id)} />
            <FollowUp prompt={promptFor('GetProjectHealth', project.code || project.name)}>{t.health}</FollowUp>
          </Footer>
        </>
      )}
    </Shell>
  );
};

export const ProjectBudgetView: React.FC<{ project?: string }> = props => (
  <ProjectGate intent="GetProjectBudget" eyebrow={strings().budget.eyebrow} title={strings().intents.GetProjectBudget.title} project={props.project}>
    {project => <Detail project={project} />}
  </ProjectGate>
);
