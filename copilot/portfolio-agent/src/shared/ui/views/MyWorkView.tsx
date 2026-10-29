import * as React from 'react';
import { Badge, Button, makeStyles, Text, tokens } from '@fluentui/react-components';
import { ChevronRight16Regular } from '@fluentui/react-icons';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, Info, Kpi, KpiGrid, Loading, Shell } from '../kit';
import { hours, shortDate } from '../format';
import { attentionItems, type AttentionItem } from '../../logic/myWork';
import { approvalQueue } from '../../logic/approvals';
import { portfolioSummary } from '../../logic/portfolio';
import { purchasingStatus } from '../../logic/purchasing';
import { resourceLoad } from '../../projectiq/load';
import { weekStart } from '../../projectiq/timesheet';
import { promptFor } from '../../intents';

const useStyles = makeStyles({
  list: { display: 'flex', flexDirection: 'column', gap: tokens.spacingVerticalXS },
  item: {
    display: 'flex', alignItems: 'center', gap: tokens.spacingHorizontalS, padding: '8px 10px', borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorNeutralBackground2, textAlign: 'left', width: '100%', justifyContent: 'flex-start',
  },
  text: { flexGrow: 1 },
});

function message(i: AttentionItem): string {
  switch (i.kind) {
    case 'timeToApprove': return `${i.count} time entries to approve (${i.detail} h)`;
    case 'requestsToApprove': return `${i.count} purchase requests waiting for your approval`;
    case 'rejectedHours': return `${i.count} of your time entries were rejected: fix and resubmit them`;
    case 'hoursToSubmit': return `${i.count} draft time entries to submit (${i.detail} h)`;
    case 'missingHours': return `${i.detail} h missing in last week's timesheet`;
    case 'projectOffTrack': return `Project ${i.detail} is off track`;
    case 'projectAtRisk': return `Project ${i.detail} is at risk`;
    case 'lateOrders': return `${i.count} purchase orders are late`;
    case 'invoicesToReview': return `${i.count} supplier invoices to review`;
    case 'overloaded': return `You are overloaded in ${i.count} of the next 4 weeks`;
    default: return '';
  }
}

const SEVERITY = { high: 'danger', medium: 'warning', low: 'informative' } as const;

export const MyWorkView: React.FC = () => {
  const s = useStyles();
  const { today, followUp, setModelContext } = useAgent();
  const monday = weekStart(today);
  const state = useServiceData(async service => {
    const me = await service.me();
    const [entries, pending, purchasing, projects, managed, load] = await Promise.all([
      service.myEntries(monday - 7, monday + 6),
      service.pendingTime(),
      service.purchasing().catch(() => undefined),
      service.projects(),
      service.managedProjectIds(),
      me.resourceId ? service.loadData(monday, monday + 27) : Promise.resolve(undefined),
    ]);
    return { me, entries, pending, purchasing, projects, managed, load };
  }, [monday]);
  const items = React.useMemo(() => {
    if (!state.data) return [];
    const d = state.data;
    const summary = portfolioSummary(d.projects.projects.filter(p => d.managed.has(p.id)), today);
    const load = d.load && d.me.resourceId
      ? resourceLoad(d.load.resources.filter(r => r.id === d.me.resourceId), d.load.allocations, d.load.absences, monday, 4)[0]
      : undefined;
    return attentionItems({
      today, monday, weeklyHours: d.me.resourceId ? d.me.weeklyHours : 0, entries: d.entries,
      approvals: approvalQueue(d.pending, today), purchasing: d.purchasing ? purchasingStatus(d.purchasing, today) : undefined,
      myProjects: summary.rows, load,
    });
  }, [state.data, today, monday]);
  React.useEffect(() => {
    if (state.data) setModelContext('What needs the user\'s attention in ProjectIQ: ' + (items.map(message).join('; ') || 'nothing'));
  }, [items]);
  const thisWeek = state.data?.entries.filter(e => e.day >= monday).reduce((t, e) => t + e.hours, 0) ?? 0;
  return (
    <Shell eyebrow="My work" title={`What needs your attention${state.data?.me.resourceName ? ', ' + state.data.me.resourceName.split(' ')[0] : ''}`}
      subtitle={`Week of ${shortDate(monday)}`} onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !state.data && <Loading />}
      {state.data && (
        <>
          <KpiGrid>
            <Kpi label="My hours this week" value={hours(thisWeek)} note={state.data.me.resourceId ? `of ${hours(state.data.me.weeklyHours)}` : 'No resource linked'} />
            <Kpi label="Projects I manage" value={String(state.data.managed.size)} />
            <Kpi label="Items" value={String(items.length)} tone={items.some(i => i.severity === 'high') ? 'danger' : 'neutral'} />
          </KpiGrid>
          {!items.length && <Info intent="success" title="All clear">Nothing needs your attention right now.</Info>}
          <div className={s.list}>
            {items.map((i, n) => (
              <Button key={n} className={s.item} appearance="subtle" icon={<ChevronRight16Regular />} iconPosition="after"
                onClick={() => followUp(i.kind === 'projectOffTrack' || i.kind === 'projectAtRisk' ? promptFor('GetProjectHealth', i.detail)
                  : i.kind === 'overloaded' ? 'Show my resource load for the next weeks' : promptFor(i.intent))}>
                <Badge color={SEVERITY[i.severity]} appearance="filled" size="extra-small" />
                <Text className={s.text}>{message(i)}</Text>
              </Button>
            ))}
          </div>
        </>
      )}
    </Shell>
  );
};
