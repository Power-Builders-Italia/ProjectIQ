import * as React from 'react';
import { Badge, Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text } from '@fluentui/react-components';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, Footer, Info, Kpi, KpiGrid, Loading, OpenInApp, Shell } from '../kit';
import { date } from '../format';
import { EXPIRING_DAYS, supplierCompliance } from '../../logic/suppliers';
import { listUrl, recordUrl } from '../../settings';
import { strings } from '../../i18n';

export const SupplierComplianceView: React.FC<{ supplier?: string }> = props => {
  const { today, wide, openLink, setModelContext } = useAgent();
  const t = strings().suppliers;
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
    <Shell eyebrow={t.eyebrow} title={one ? one.supplier.name : strings().intents.GetSupplierCompliance.title}
      subtitle={one ? undefined : t.subtitle(EXPIRING_DAYS)} onRefresh={state.reload}>
      {state.error && <ErrorBar error={state.error} />}
      {state.loading && !state.data && <Loading />}
      {state.data && (
        <>
          {one && (
            <Info intent={one.canOrder ? 'success' : 'error'} title={one.canOrder ? t.canOrder : t.cannotOrder}>
              {t.states[one.state]} · {t.openOrders(one.supplier.openOrders)}
            </Info>
          )}
          {!one && (
            <KpiGrid>
              <Kpi label={t.blocked} value={String(list.filter(c => c.state === 'blocked').length)} tone="danger" />
              <Kpi label={t.withExpired} value={String(list.filter(c => c.state === 'expired').length)} tone="danger" />
              <Kpi label={t.expiring} value={String(list.filter(c => c.state === 'expiring').length)} tone="warning" />
            </KpiGrid>
          )}
          {!list.length && <Info>{props.supplier ? t.noMatch(props.supplier) : t.allOk}</Info>}
          {!!list.length && (
            <Table size="small" aria-label={t.table}>
              <TableHeader>
                <TableRow>
                  {!one && <TableHeaderCell>{t.supplier}</TableHeaderCell>}
                  <TableHeaderCell>{t.document}</TableHeaderCell>
                  <TableHeaderCell style={{ width: 110 }}>{t.expiry}</TableHeaderCell>
                  <TableHeaderCell style={{ width: 130 }}>{t.state}</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.slice(0, one || wide ? 200 : 10).flatMap(c => (c.documents.length ? c.documents : [undefined]).map((d, i) => (
                  <TableRow key={`${c.supplier.id}-${d?.id || i}`} style={{ cursor: 'pointer' }}
                    onClick={() => openLink(recordUrl(state.data!.settings, 'account', c.supplier.id))}>
                    {!one && <TableCell>{i === 0 ? <Text weight="semibold">{c.supplier.name}</Text> : ''}</TableCell>}
                    <TableCell>{d ? `${d.type || ''} ${d.description}${d.number ? ' · ' + d.number : ''}`.trim() : t.noDocument}</TableCell>
                    <TableCell>{d ? date(d.expiry) : '–'}</TableCell>
                    <TableCell>
                      {d?.state === 'expired' && <Badge color="danger" appearance="tint">{t.expiredAgo(-(d.daysLeft || 0))}</Badge>}
                      {d?.state === 'expiring' && <Badge color="warning" appearance="tint">{t.daysLeft(d.daysLeft || 0)}</Badge>}
                      {d?.state === 'valid' && <Badge color="success" appearance="tint">{t.valid}</Badge>}
                      {i === 0 && c.supplier.blocked && <> <Badge color="severe">{t.states.blocked}</Badge></>}
                    </TableCell>
                  </TableRow>
                )))}
              </TableBody>
            </Table>
          )}
          <Text size={200}>{t.note}</Text>
          <Footer><OpenInApp url={listUrl(state.data.settings, 'op365_supplierdocument')} label={t.openList} /></Footer>
        </>
      )}
    </Shell>
  );
};
