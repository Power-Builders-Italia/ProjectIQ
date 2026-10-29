import * as React from 'react';
import { Text, tokens } from '@fluentui/react-components';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, FollowUp, Footer, Info, Kpi, KpiGrid, Loading, OpenInApp, Shell } from '../kit';
import { date, shortDate } from '../format';
import { ProjectGate } from './ProjectGate';
import { timelineRows, type TimelineRow } from '../../logic/project';
import type { ProjectFigures } from '../../logic/portfolio';
import { promptFor } from '../../intents';
import { recordUrl } from '../../settings';

const Gantt: React.FC<{ rows: TimelineRow[]; start: number; end: number; today: number }> = ({ rows, start, end, today }) => {
  const W = 640, labelW = 170, rowH = 24, top = 18;
  const span = Math.max(1, end - start + 1);
  const x = (d: number): number => labelW + (d - start) / span * (W - labelW - 4);
  const height = top + rows.length * rowH + 4;
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${height}`} role="img" aria-label="Timeline of the WBS phases" preserveAspectRatio="xMinYMin meet">
      <text x={labelW} y={11} fontSize={10} fill={tokens.colorNeutralForeground3}>{shortDate(start)}</text>
      <text x={W - 4} y={11} fontSize={10} textAnchor="end" fill={tokens.colorNeutralForeground3}>{shortDate(end)}</text>
      {today >= start && today <= end && (
        <line x1={x(today)} x2={x(today)} y1={top - 4} y2={height} stroke={tokens.colorPaletteRedBorder2} strokeDasharray="3 3" />
      )}
      {rows.map((r, i) => {
        const y = top + i * rowH;
        const summary = r.node.children.length > 0;
        const fill = r.critical ? tokens.colorPaletteRedBackground3 : summary ? tokens.colorNeutralForeground3 : tokens.colorBrandBackground;
        return (
          <g key={r.node.id}>
            <text x={4 + r.node.level * 10} y={y + 15} fontSize={11} fontWeight={summary ? 600 : 400} fill={tokens.colorNeutralForeground1}>
              {`${r.node.code} ${r.node.name}`.substring(0, 28)}
            </text>
            {r.baselineStart !== undefined && r.baselineEnd !== undefined && (
              <rect x={x(r.baselineStart)} y={y + 16} width={Math.max(2, x(r.baselineEnd + 1) - x(r.baselineStart))} height={4} rx={2}
                fill={tokens.colorNeutralStroke1} />
            )}
            {r.start !== undefined && r.end !== undefined && (
              <>
                <rect x={x(r.start)} y={y + 4} width={Math.max(2, x(r.end + 1) - x(r.start))} height={summary ? 8 : 11} rx={2} fill={fill} opacity={0.35} />
                <rect x={x(r.start)} y={y + 4} width={Math.max(0, (x(r.end + 1) - x(r.start)) * Math.min(100, r.node.rollProgress) / 100)}
                  height={summary ? 8 : 11} rx={2} fill={fill} />
              </>
            )}
            {r.pushedEnd !== undefined && r.end !== undefined && (
              <rect x={x(r.end + 1)} y={y + 4} width={Math.max(2, x(r.pushedEnd + 1) - x(r.end + 1))} height={11} fill="none"
                stroke={tokens.colorPaletteDarkOrangeBorder2} strokeDasharray="3 2" />
            )}
          </g>
        );
      })}
    </svg>
  );
};

const Detail: React.FC<{ project: ProjectFigures }> = ({ project }) => {
  const { today, wide, setModelContext } = useAgent();
  const state = useServiceData(async (service, settings) => ({ detail: await service.projectDetail(project.id), settings }), [project.id]);
  const timeline = React.useMemo(() => state.data
    ? timelineRows(state.data.detail.nodes, state.data.detail.links, today, wide ? 1 : 0, state.data.detail.baseline?.nodes)
    : undefined, [state.data, today, wide]);
  const late = timeline?.rows.filter(r => r.late) || [];
  const critical = timeline?.rows.filter(r => r.critical && r.node.level === 0) || [];
  const slips = timeline?.rows.filter(r => r.node.level === 0 && r.end !== undefined && r.baselineEnd !== undefined && r.end > r.baselineEnd) || [];
  React.useEffect(() => {
    if (!timeline) return;
    setModelContext(`Timeline of project ${project.code} ${project.name}: ` + timeline.rows.map(r => `${r.node.code} ${r.node.name} ${date(r.start)}-${date(r.end)} `
      + `progress ${r.node.rollProgress}%${r.critical ? ' critical' : ''}${r.late ? ' late' : ''}`
      + `${r.baselineEnd !== undefined ? ` baseline end ${date(r.baselineEnd)}` : ''}${r.pushedEnd !== undefined ? ` pushed to ${date(r.pushedEnd)}` : ''}`).join('; '));
  }, [timeline]);
  return (
    <Shell eyebrow="Project timeline" title={`${project.code} ${project.name}`.trim()} subtitle={`${date(project.start)} → ${date(project.end)}`} onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !timeline && <Loading />}
      {timeline && state.data && (
        <>
          <KpiGrid>
            <Kpi label="Late phases" value={String(late.filter(r => r.node.level === 0).length)} tone={late.length ? 'danger' : 'neutral'} />
            <Kpi label="Critical phases" value={String(critical.length)} />
            <Kpi label="Later than baseline" value={state.data.detail.baseline ? String(slips.length) : '–'}
              note={state.data.detail.baseline ? state.data.detail.baseline.name : 'No reference baseline'} tone={slips.length ? 'warning' : 'neutral'} />
          </KpiGrid>
          {timeline.start !== undefined && timeline.end !== undefined
            ? <Gantt rows={timeline.rows} start={timeline.start} end={timeline.end} today={today} />
            : <Info>The WBS has no dates yet.</Info>}
          <Text size={200}>Bars show progress; red = critical path, grey line = reference baseline, dashed = pushed by dependencies, red dashed line = today.</Text>
          <Footer>
            <OpenInApp url={recordUrl(state.data.settings, 'op365_project', project.id)} label="Open the Gantt in ProjectIQ" />
            <FollowUp prompt={promptFor('GetProjectHealth', project.code || project.name)}>Project health</FollowUp>
          </Footer>
        </>
      )}
    </Shell>
  );
};

export const ProjectTimelineView: React.FC<{ project?: string }> = props => (
  <ProjectGate intent="GetProjectTimeline" eyebrow="Project timeline" title="Project timeline" project={props.project}>
    {project => <Detail project={project} />}
  </ProjectGate>
);
