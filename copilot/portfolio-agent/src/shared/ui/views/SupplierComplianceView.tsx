import * as React from 'react';
import { Badge, Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text } from '@fluentui/react-components';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, Footer, Info, Kpi, KpiGrid, Loading, OpenInApp, Shell } from '../kit';
import { date } from '../format';
import { EXPIRING_DAYS, supplierCompliance, type SupplierCompliance } from '../../logic/suppliers';
import { listUrl, recordUrl } from '../../settings';

const STATE: Record<SupplierCompliance['state'], { label: string; color: 'danger' | 'warning' | 'success' | 'severe' }> = {
  blocked: { label: 'Blocked', color: 'severe' },
  expired: { label: 'Expired documents', color: 'danger' },
  expiring: { label: 'Expiring soon', color: 'warning' },
  ok: { label: 'Compliant', color: 'success' },
};

export const SupplierComplianceView: React.FC<{ supplier?: string }> = props => {
  const { today, wide, openLink, setModelContext } = useAgent();
  const state = useServiceData(async (service, settings) => ({ ...(await service.suppliers(today + EXPIRING_DAYS, props.supplier)), settings }),
    [props.supplier, today]);
  const list = React.useMemo(() => (state.data ? supplierCompliance(state.data.suppliers, state.data.documents, today) : []), [state.data, today]);
  React.useEffect(() => {
    if (!state.data) return;
    setModelContext('Supplier compliance: ' + list.slice(0, 50).map(c => `${c.supplier.name}: ${c.state}, can order ${c.canOrder ? 'yes' : 'no'}, `
      + c.documents.map(d => `${d.type || d.description} ${d.number || ''} expires ${date(d.expiry)}`).join(', ')).join('\n'));
  }, [list]);
  const one = props.supplier && list.length === 1 ? list[0] : undefined;
  return (
    <Shell eyebrow="Purchasing" title={one ? one.supplier.name : 'Supplier compliance'}
      subtitle={one ? undefined : `Expired documents and documents expiring in ${EXPIRING_DAYS} days`} onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !state.data && <Loading />}
      {state.data && (
        <>
          {one && (
            <Info intent={one.canOrder ? 'success' : 'error'} title={one.canOrder ? 'You can order from this supplier' : 'Do not order from this supplier'}>
              {STATE[one.state].label} · {one.supplier.openOrders} open orders.
            </Info>
          )}
          {!one && (
            <KpiGrid>
              <Kpi label="Blocked" value={String(list.filter(c => c.state === 'blocked').length)} tone="danger" />
              <Kpi label="With expired documents" value={String(list.filter(c => c.state === 'expired').length)} tone="danger" />
              <Kpi label="Expiring soon" value={String(list.filter(c => c.state === 'expiring').length)} tone="warning" />
            </KpiGrid>
          )}
          {!list.length && <Info>{props.supplier ? `No supplier matches "${props.supplier}".` : 'All suppliers are compliant.'}</Info>}
          {!!list.length && (
            <Table size="small" aria-label="Supplier documents">
              <TableHeader>
                <TableRow>
                  {!one && <TableHeaderCell>Supplier</TableHeaderCell>}
                  <TableHeaderCell>Document</TableHeaderCell>
                  <TableHeaderCell style={{ width: 110 }}>Expiry</TableHeaderCell>
                  <TableHeaderCell style={{ width: 130 }}>State</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.slice(0, one || wide ? 200 : 10).flatMap(c => (c.documents.length ? c.documents : [undefined]).map((d, i) => (
                  <TableRow key={`${c.supplier.id}-${d?.id || i}`} style={{ cursor: 'pointer' }}
                    onClick={() => openLink(recordUrl(state.data!.settings, 'account', c.supplier.id))}>
                    {!one && <TableCell>{i === 0 ? <Text weight="semibold">{c.supplier.name}</Text> : ''}</TableCell>}
                    <TableCell>{d ? `${d.type || ''} ${d.description}${d.number ? ' · ' + d.number : ''}`.trim() : 'No document'}</TableCell>
                    <TableCell>{d ? date(d.expiry) : '–'}</TableCell>
                    <TableCell>
                      {d?.state === 'expired' && <Badge color="danger" appearance="tint">Expired {-(d.daysLeft || 0)} d ago</Badge>}
                      {d?.state === 'expiring' && <Badge color="warning" appearance="tint">{d.daysLeft} d left</Badge>}
                      {d?.state === 'valid' && <Badge color="success" appearance="tint">Valid</Badge>}
                      {i === 0 && c.supplier.blocked && <> <Badge color="severe">Blocked</Badge></>}
                    </TableCell>
                  </TableRow>
                )))}
              </TableBody>
            </Table>
          )}
          <Text size={200}>Renewed documents are uploaded on the supplier form in ProjectIQ, or by the supplier in the supplier portal.</Text>
          <Footer><OpenInApp url={listUrl(state.data.settings, 'op365_supplierdocument')} label="Open supplier documents" /></Footer>
        </>
      )}
    </Shell>
  );
};
