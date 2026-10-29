import * as React from 'react';
import { makeStyles, mergeClasses, Text, tokens, Tooltip } from '@fluentui/react-components';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, Footer, Info, Kpi, KpiGrid, Loading, OpenInApp, Shell } from '../kit';
import { hours, pct, shortDate } from '../format';
import { level, resourceLoad, type LoadLevel } from '../../projectiq/load';
import { weekStart } from '../../projectiq/timesheet';
import { resolveDay } from '../../logic/timesheetDraft';
import { listUrl } from '../../settings';
import { EN, strings } from '../../i18n';

const useStyles = makeStyles({
  grid: { display: 'grid', gap: '2px', alignItems: 'stretch', overflowX: 'auto' },
  head: { fontSize: tokens.fontSizeBase100, color: tokens.colorNeutralForeground3, textAlign: 'center', padding: '2px' },
  name: { fontSize: tokens.fontSizeBase200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', padding: '4px 6px 4px 0' },
  cell: { fontSize: tokens.fontSizeBase100, textAlign: 'center', padding: '4px 2px', borderRadius: tokens.borderRadiusSmall },
  free: { backgroundColor: tokens.colorNeutralBackground3, color: tokens.colorNeutralForeground3 },
  ok: { backgroundColor: tokens.colorPaletteGreenBackground2, color: tokens.colorPaletteGreenForeground2 },
  full: { backgroundColor: tokens.colorPaletteYellowBackground2, color: tokens.colorPaletteMarigoldForeground2 },
  over: { backgroundColor: tokens.colorPaletteRedBackground2, color: tokens.colorPaletteRedForeground2, fontWeight: tokens.fontWeightSemibold },
});

export interface ResourceLoadProps { resource?: string; from?: string; weeks?: number; }

export const ResourceLoadView: React.FC<ResourceLoadProps> = props => {
  const s = useStyles();
  const { today, wide, setModelContext } = useAgent();
  const str = strings();
  const t = str.load;
  const first = weekStart(resolveDay(props.from, today) ?? today);
  const weeks = Math.min(26, Math.max(1, Math.round(props.weeks || (wide ? 12 : 6))));
  const state = useServiceData(async (service, settings) => {
    const [data, me] = await Promise.all([service.loadData(first, first + weeks * 7 - 1), service.me()]);
    return { ...data, me, settings };
  }, [first, weeks]);
  const rows = React.useMemo(() => {
    if (!state.data) return [];
    const q = (props.resource || '').trim().toLowerCase();
    const mine = EN.load.me.indexOf(q) >= 0 || t.me.indexOf(q) >= 0;
    const resources = state.data.resources.filter(r => !q || (mine ? r.id === state.data!.me.resourceId : r.name.toLowerCase().indexOf(q) >= 0));
    return resourceLoad(resources, state.data.allocations, state.data.absences, first, weeks);
  }, [state.data, props.resource, first, weeks]);
  const overCells = rows.reduce((n, r) => n + r.weeks.filter(w => level(w) === 'over').length, 0);
  const overPeople = rows.filter(r => r.weeks.some(w => level(w) === 'over'));
  const free = rows.reduce((n, r) => n + r.weeks.reduce((t, w) => t + Math.max(0, w.capacity - w.load), 0), 0);
  React.useEffect(() => {
    if (!state.data) return;
    setModelContext(`Resource load from ${shortDate(first)} for ${weeks} weeks (allocated hours / capacity): `
      + rows.slice(0, 60).map(r => `${r.resource.name}: ` + r.weeks.map((w, i) => `${shortDate(first + i * 7)} ${Math.round(w.load)}/${Math.round(w.capacity)}`).join(', ')).join('\n'));
  }, [rows]);
  return (
    <Shell eyebrow={t.eyebrow} title={str.intents.GetResourceLoad.title} subtitle={`${props.resource ? props.resource + ' · ' : ''}${t.subtitle(weeks, shortDate(first))}`} onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !state.data && <Loading />}
      {state.data && (
        <>
          <KpiGrid>
            <Kpi label={t.overloaded} value={String(overPeople.length)} note={t.overCells(overCells)} tone={overPeople.length ? 'danger' : 'success'} />
            <Kpi label={t.free} value={hours(Math.round(free))} note={t.freeNote} />
            <Kpi label={t.people} value={String(rows.length)} />
          </KpiGrid>
          {!rows.length && <Info>{props.resource ? t.noMatch(props.resource) : t.none}</Info>}
          {!!rows.length && (
            <div className={s.grid} style={{ gridTemplateColumns: `minmax(110px, 1.4fr) repeat(${weeks}, minmax(38px, 1fr))` }}>
              <span />
              {Array.from({ length: weeks }, (_, i) => <span key={i} className={s.head}>{shortDate(first + i * 7)}</span>)}
              {rows.slice(0, wide ? 200 : 10).map(r => (
                <React.Fragment key={r.resource.id}>
                  <span className={s.name} title={r.resource.name}>{r.resource.name}</span>
                  {r.weeks.map((w, i) => {
                    const l = level(w);
                    const tip = t.cell(r.resource.name, shortDate(first + i * 7), hours(Math.round(w.load * 10) / 10), hours(Math.round(w.capacity * 10) / 10))
                      + (w.projects.size ? ' · ' + [...w.projects.entries()].map(([p, h]) => `${p} ${Math.round(h)} h`).join(', ') : '');
                    return (
                      <Tooltip key={i} content={tip} relationship="description">
                        <span className={mergeClasses(s.cell, s[l])} tabIndex={0}>
                          {w.capacity > 0 ? pct(w.load / w.capacity) : w.load > 0 ? `${Math.round(w.load)} h` : '–'}
                        </span>
                      </Tooltip>
                    );
                  })}
                </React.Fragment>
              ))}
            </div>
          )}
          {!wide && rows.length > 10 && <Text size={200}>{t.more(rows.length - 10)}</Text>}
          <Text size={200}>{t.legend((['free', 'ok', 'full', 'over'] as LoadLevel[]).map(l => t.levels[l]).join(' · '))}</Text>
          <Footer><OpenInApp url={listUrl(state.data.settings, 'op365_wbsallocation')} label={t.openList} /></Footer>
        </>
      )}
    </Shell>
  );
};
