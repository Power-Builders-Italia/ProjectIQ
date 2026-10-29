import * as React from 'react';
import { Badge, Tab, TabList, Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text } from '@fluentui/react-components';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, Footer, Info, Kpi, KpiGrid, Loading, OpenInApp, Shell } from '../kit';
import { date, money } from '../format';
import { matchProjects } from '../../logic/portfolio';
import { purchasingStatus } from '../../logic/purchasing';
import { listUrl, recordUrl, type AgentSettings } from '../../settings';
import { strings } from '../../i18n';

type Focus = 'approvals' | 'orders' | 'rfqs' | 'invoices';

export interface PurchasingProps { project?: string; focus?: Focus; }

interface Line { id: string; table: string; cells: React.ReactNode[]; }

const Grid: React.FC<{ head: string[]; lines: Line[]; settings: AgentSettings; empty: string }> = ({ head, lines, settings, empty }) => {
  const { openLink, wide } = useAgent();
  if (!lines.length) return <Info>{empty}</Info>;
  return (
    <Table size="small">
      <TableHeader><TableRow>{head.map(h => <TableHeaderCell key={h}>{h}</TableHeaderCell>)}</TableRow></TableHeader>
      <TableBody>
        {lines.slice(0, wide ? 200 : 8).map(l => (
          <TableRow key={l.id} onClick={() => openLink(recordUrl(settings, l.table, l.id))} style={{ cursor: 'pointer' }}>
            {l.cells.map((c, i) => <TableCell key={i}>{c}</TableCell>)}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export const PurchasingView: React.FC<PurchasingProps> = props => {
  const { today, setModelContext } = useAgent();
  const t = strings().purchasing;
  const state = useServiceData(async (service, settings) => {
    let projectId: string | undefined;
    let projectLabel: string | undefined;
    if (props.project) {
      const { projects } = await service.projects(true);
      const m = matchProjects(projects, props.project);
      if (m.length === 1) { projectId = m[0].id; projectLabel = `${m[0].code} ${m[0].name}`.trim(); }
    }
    return { data: await service.purchasing(projectId), settings, projectLabel };
  }, [props.project]);
  const [tab, setTab] = React.useState<Focus>(props.focus || 'approvals');
  const status = state.data ? purchasingStatus(state.data.data, today) : undefined;
  React.useEffect(() => {
    if (!status) return;
    setModelContext(`Purchasing${state.data?.projectLabel ? ' of ' + state.data.projectLabel : ''}: `
      + `requests to approve by me ${status.toApprove.map(r => `${r.number} ${r.title} ${r.amount}`).join(', ') || 'none'}; `
      + `approved requests to order ${status.toOrder.length}; RFQs past deadline ${status.rfqsToClose.map(r => r.number).join(', ') || 'none'}; `
      + `late orders ${status.lateOrders.map(o => `${o.number} ${o.supplier} ${o.daysLate} days late`).join(', ') || 'none'}; `
      + `invoices to review ${status.invoicesToReview.map(i => `${i.number} ${i.supplier} ${i.total}`).join(', ') || 'none'}; committed ${status.committed}.`);
  }, [status]);
  const notFound = props.project && state.data && !state.data.projectLabel;
  return (
    <Shell eyebrow={t.eyebrow} title={t.title} subtitle={state.data?.projectLabel || t.allProjects} onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !state.data && <Loading />}
      {notFound && <Info intent="warning">{t.notFound(props.project as string)}</Info>}
      {status && state.data && (
        <>
          <KpiGrid>
            <Kpi label={t.toApprove} value={String(status.toApprove.length)} tone={status.toApprove.length ? 'warning' : 'neutral'} />
            <Kpi label={t.toOrder} value={String(status.toOrder.length)} />
            <Kpi label={t.lateOrders} value={String(status.lateOrders.length)} tone={status.lateOrders.length ? 'danger' : 'neutral'} />
            <Kpi label={t.invoices} value={String(status.invoicesToReview.length)} />
            <Kpi label={t.committed} value={money(status.committed, undefined, true)} note={t.committedNote} />
          </KpiGrid>
          <TabList selectedValue={tab} onTabSelect={(_, d) => setTab(d.value as Focus)} size="small">
            <Tab value="approvals">{t.tabRequests(status.toApprove.length + status.toOrder.length + status.submitted.length)}</Tab>
            <Tab value="rfqs">{t.tabRfqs(status.rfqsToClose.length)}</Tab>
            <Tab value="orders">{t.tabOrders(status.lateOrders.length + status.openOrders.length)}</Tab>
            <Tab value="invoices">{t.tabInvoices(status.invoicesToReview.length)}</Tab>
          </TabList>
          {tab === 'approvals' && (
            <Grid settings={state.data.settings} empty={t.noRequest} head={[t.request, t.project, t.amount, t.neededBy, t.status]}
              lines={[...status.toApprove, ...status.submitted, ...status.toOrder].map(r => ({
                id: r.id, table: 'op365_purchaserequest', cells: [
                  <><Text weight="semibold">{r.number}</Text> {r.title}</>, r.project, money(r.amount), date(r.neededBy),
                  <>{status.toApprove.indexOf(r) >= 0 ? <Badge color="warning">{t.yourApproval}</Badge> : status.toOrder.indexOf(r) >= 0
                    ? <Badge color="brand">{t.toOrder}</Badge> : <Badge color="informative">{t.submitted}</Badge>}
                    {r.overBudget && <> <Badge color="danger" appearance="tint">{t.overBudget}</Badge></>}
                    {r.aboveThreshold && <> <Badge appearance="outline">{t.aboveThreshold}</Badge></>}</>,
                ] }))} />
          )}
          {tab === 'rfqs' && (
            <Grid settings={state.data.settings} empty={t.noRfq} head={[t.rfq, t.project, t.deadline, t.responses]}
              lines={status.rfqsToClose.map(r => ({ id: r.id, table: 'op365_rfq', cells: [r.number, r.project, date(r.deadline), String(r.responses)] }))} />
          )}
          {tab === 'orders' && (
            <Grid settings={state.data.settings} empty={t.noOrder} head={[t.order, t.supplier, t.project, t.expected, t.toReceive]}
              lines={[...status.lateOrders, ...status.openOrders].map(o => ({ id: o.id, table: 'op365_purchaseorder', cells: [
                o.number, o.supplier, o.project,
                <>{date(o.expected)}{'daysLate' in o && <> <Badge color="danger" appearance="tint">{t.daysLate((o as { daysLate: number }).daysLate)}</Badge></>}</>,
                money(Math.max(0, o.total - o.received)),
              ] }))} />
          )}
          {tab === 'invoices' && (
            <Grid settings={state.data.settings} empty={t.noInvoice} head={[t.invoice, t.supplier, t.date, t.total, t.order]}
              lines={status.invoicesToReview.map(i => ({ id: i.id, table: 'op365_supplierinvoice', cells: [
                <><Text weight="semibold">{i.number}</Text> {i.invoiceNumber}</>, i.supplier, date(i.date), money(i.total), i.order || '–',
              ] }))} />
          )}
          <Text size={200}>{t.note}</Text>
          <Footer><OpenInApp url={listUrl(state.data.settings, 'op365_purchaserequest')} label={t.openList} /></Footer>
        </>
      )}
    </Shell>
  );
};
