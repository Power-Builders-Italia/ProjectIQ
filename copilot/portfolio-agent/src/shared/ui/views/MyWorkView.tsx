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
import { EN, strings, type Strings } from '../../i18n';

const useStyles = makeStyles({
  list: { display: 'flex', flexDirection: 'column', gap: tokens.spacingVerticalXS },
  item: {
    display: 'flex', alignItems: 'center', gap: tokens.spacingHorizontalS, padding: '8px 10px', borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorNeutralBackground2, textAlign: 'left', width: '100%', justifyContent: 'flex-start',
  },
  text: { flexGrow: 1 },
});

function message(i: AttentionItem, s: Strings = strings()): string {
  const t = s.myWork;
  const detail = i.detail || '';
  switch (i.kind) {
    case 'timeToApprove': return t.timeToApprove(i.count, detail);
    case 'requestsToApprove': return t.requestsToApprove(i.count);
    case 'rejectedHours': return t.rejectedHours(i.count);
    case 'hoursToSubmit': return t.hoursToSubmit(i.count, detail);
    case 'missingHours': return t.missingHours(detail);
    case 'projectOffTrack': return t.projectOffTrack(detail);
    case 'projectAtRisk': return t.projectAtRisk(detail);
    case 'lateOrders': return t.lateOrders(i.count);
    case 'invoicesToReview': return t.invoicesToReview(i.count);
    case 'overloaded': return t.overloaded(i.count);
    default: return '';
  }
}

const SEVERITY = { high: 'danger', medium: 'warning', low: 'informative' } as const;

export const MyWorkView: React.FC = () => {
  const c = useStyles();
  const { today, followUp, setModelContext } = useAgent();
  const s = strings();
  const t = s.myWork;
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
    if (state.data) setModelContext('What needs the user\'s attention in ProjectIQ: ' + (items.map(i => message(i, EN)).join('; ') || 'nothing'));
  }, [items]);
  const thisWeek = state.data?.entries.filter(e => e.day >= monday).reduce((t, e) => t + e.hours, 0) ?? 0;
  return (
    <Shell eyebrow={t.eyebrow} title={state.data?.me.resourceName ? t.titleNamed(state.data.me.resourceName.split(' ')[0]) : t.title}
      subtitle={s.common.weekOf(shortDate(monday))} onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !state.data && <Loading />}
      {state.data && (
        <>
          <KpiGrid>
            <Kpi label={t.myHours} value={hours(thisWeek)} note={state.data.me.resourceId ? t.ofHours(hours(state.data.me.weeklyHours)) : t.noResource} />
            <Kpi label={t.managed} value={String(state.data.managed.size)} />
            <Kpi label={t.items} value={String(items.length)} tone={items.some(i => i.severity === 'high') ? 'danger' : 'neutral'} />
          </KpiGrid>
          {!items.length && <Info intent="success" title={t.allClear}>{t.nothing}</Info>}
          <div className={c.list}>
            {items.map((i, n) => (
              <Button key={n} className={c.item} appearance="subtle" icon={<ChevronRight16Regular />} iconPosition="after"
                onClick={() => followUp(i.kind === 'projectOffTrack' || i.kind === 'projectAtRisk' ? promptFor('GetProjectHealth', i.detail)
                  : i.kind === 'overloaded' ? s.prompts.myResourceLoad : promptFor(i.intent))}>
                <Badge color={SEVERITY[i.severity]} appearance="filled" size="extra-small" />
                <Text className={c.text}>{message(i, s)}</Text>
              </Button>
            ))}
          </div>
        </>
      )}
    </Shell>
  );
};
