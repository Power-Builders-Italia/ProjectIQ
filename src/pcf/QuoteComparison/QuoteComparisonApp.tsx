import * as React from "react";
import {
    Badge, Button, Dialog, DialogActions, DialogBody, DialogContent, DialogSurface, DialogTitle, FluentProvider, MessageBar,
    MessageBarBody, Spinner, Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Toolbar, ToolbarButton,
    makeStyles, tokens, webLightTheme, Theme,
} from "@fluentui/react-components";
import { IInputs } from "./generated/ManifestTypes";
import { hostRecordId } from "../shared/data";
import { callAction } from "../shared/execution";
import { loadRfq, RFQ_SENT } from "../shared/purchasing";
import { compareQuotes, Comparison, INVITATION_RESPONDED, QuoteInvitation } from "../shared/quotes";
import { RefreshIcon } from "../shared/icons";

const useStyles = makeStyles({
    root: { display: "flex", flexDirection: "column", gap: tokens.spacingVerticalS, width: "100%" },
    scroll: { overflowX: "auto" },
    num: { textAlign: "right", whiteSpace: "nowrap" },
    head: { display: "flex", flexDirection: "column", alignItems: "flex-end", gap: tokens.spacingVerticalXXS },
    sub: { color: tokens.colorNeutralForeground3, fontSize: tokens.fontSizeBase200 },
    best: { backgroundColor: tokens.colorPaletteGreenBackground1 },
    total: { fontWeight: tokens.fontWeightSemibold },
    bestColumn: { backgroundColor: tokens.colorNeutralBackground3 },
});

interface Props {
    context: ComponentFramework.Context<IInputs>;
    refreshKey: number;
}

const STATUS_KEY: Record<number, string> = {
    1: "Status_ToInvite", 365000000: "Status_Invited", 365000001: "Status_Responded", 365000002: "Status_Declined",
};

export function QuoteComparisonApp({ context, refreshKey }: Props): React.ReactElement {
    const styles = useStyles();
    const s = (key: string): string => context.resources.getString(key);
    const theme = (context as unknown as { fluentDesignLanguage?: { tokenTheme?: Theme } }).fluentDesignLanguage?.tokenTheme ?? webLightTheme;
    const rfqId = hostRecordId(context as ComponentFramework.Context<unknown>);
    const width = context.mode.allocatedWidth;
    const fill: React.CSSProperties = { width: width > 0 ? `${width}px` : "100%" };

    const [data, setData] = React.useState<{ status: number; comparison: Comparison; symbol?: string }>();
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string>();
    const [reload, setReload] = React.useState(0);
    const [award, setAward] = React.useState<QuoteInvitation>();
    const [busy, setBusy] = React.useState(false);

    React.useEffect(() => {
        if (!rfqId) { setLoading(false); return; }
        let cancelled = false;
        const load = async (): Promise<void> => {
            setLoading(true);
            try {
                const rfq = await loadRfq(context.webAPI, rfqId);
                if (cancelled) return;
                setData({ status: rfq.status, comparison: compareQuotes(rfq.lines, rfq.invitations, rfq.quotes), symbol: rfq.currencySymbol });
                setError(undefined);
            } catch (e) {
                if (!cancelled) setError(`${s("Error_Load")}: ${(e as Error).message}`);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        void load();
        return () => { cancelled = true; };
    }, [rfqId, refreshKey, reload]);

    if (!rfqId) {
        return <FluentProvider theme={theme}><MessageBar><MessageBarBody>{s("Save_Rfq")}</MessageBarBody></MessageBar></FluentProvider>;
    }
    // amounts in the quotes' currency (#33)
    const money = (v: number): string => context.formatting.formatCurrency(v, 2, data?.symbol);
    const qty = (v: number): string => context.formatting.formatDecimal(v, v % 1 === 0 ? 0 : 3);

    const doAward = async (): Promise<void> => {
        if (!award) return;
        setBusy(true);
        try {
            const result = await callAction(`op365_rfqs(${rfqId})/Microsoft.Dynamics.CRM.op365_AwardRfq`, { InvitationId: award.id });
            setAward(undefined);
            const orderId = result.PurchaseOrderId as string | undefined;
            if (orderId) void context.navigation.openForm({ entityName: "op365_purchaseorder", entityId: orderId });
            setReload(r => r + 1);
        } catch (e) {
            setError((e as Error).message);
            setAward(undefined);
        } finally {
            setBusy(false);
        }
    };

    const c = data?.comparison;
    const invitations = c?.totals.map(t => t.invitation) ?? [];
    const canAward = data?.status === RFQ_SENT;

    return (
        <FluentProvider theme={theme} style={fill}>
            <div className={styles.root}>
                <Toolbar size="small">
                    <ToolbarButton icon={<RefreshIcon />} onClick={() => setReload(r => r + 1)}>{s("Refresh")}</ToolbarButton>
                    {loading && <Spinner size="tiny" />}
                </Toolbar>
                {error && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>}
                {c && c.rows.length === 0 && <MessageBar><MessageBarBody>{s("No_Lines")}</MessageBarBody></MessageBar>}
                {c && c.rows.length > 0 && invitations.length === 0 && <MessageBar><MessageBarBody>{s("No_Invitations")}</MessageBarBody></MessageBar>}
                {c && c.rows.length > 0 && invitations.length > 0 && (
                    <div className={styles.scroll}>
                        <Table size="small" aria-label={s("Control_Name")}>
                            <TableHeader>
                                <TableRow>
                                    <TableHeaderCell>{s("Column_Line")}</TableHeaderCell>
                                    <TableHeaderCell className={styles.num}>{s("Column_Quantity")}</TableHeaderCell>
                                    {invitations.map(inv => (
                                        <TableHeaderCell key={inv.id}>
                                            <div className={styles.head}>
                                                <span>{inv.name}</span>
                                                <Badge size="small" appearance="tint"
                                                    color={inv.status === INVITATION_RESPONDED ? "success" : inv.status === 365000002 ? "danger" : "informative"}>
                                                    {s(STATUS_KEY[inv.status] ?? "Status_Invited")}
                                                </Badge>
                                            </div>
                                        </TableHeaderCell>
                                    ))}
                                    <TableHeaderCell className={`${styles.num} ${styles.bestColumn}`}>{s("Column_Best")}</TableHeaderCell>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {c.rows.map(r => (
                                    <TableRow key={r.line.id}>
                                        <TableCell>{r.line.name}</TableCell>
                                        <TableCell className={styles.num}>{qty(r.line.quantity)} {r.line.uom}</TableCell>
                                        {invitations.map(inv => {
                                            const cell = r.cells.get(inv.id);
                                            return (
                                                <TableCell key={inv.id} className={`${styles.num} ${cell?.best ? styles.best : ""}`}>
                                                    {cell ? <>{money(cell.price)}<div className={styles.sub}>{money(cell.amount)}</div></> : s("Not_Quoted")}
                                                </TableCell>
                                            );
                                        })}
                                        <TableCell className={`${styles.num} ${styles.bestColumn}`}>
                                            {r.bestPrice !== undefined ? <>
                                                {money(r.bestPrice)}
                                                <div className={styles.sub}>{invitations.find(i => i.id === r.bestInvitationId)?.name}</div>
                                            </> : s("Not_Quoted")}
                                        </TableCell>
                                    </TableRow>
                                ))}
                                <TableRow>
                                    <TableCell className={styles.total}>{s("Total")}</TableCell>
                                    <TableCell />
                                    {c.totals.map(t => (
                                        <TableCell key={t.invitation.id} className={`${styles.num} ${styles.total} ${t.best ? styles.best : ""}`}>
                                            {money(t.total)}
                                            {!t.complete && t.quoted > 0 && (
                                                <div className={styles.sub}>{s("Incomplete").replace("{0}", String(t.quoted)).replace("{1}", String(c.rows.length))}</div>
                                            )}
                                            {t.best && <div><Badge size="small" color="success">{s("Best_Total")}</Badge></div>}
                                        </TableCell>
                                    ))}
                                    <TableCell className={`${styles.num} ${styles.total} ${styles.bestColumn}`}>
                                        {money(c.rows.reduce((t, r) => t + (r.bestPrice ?? 0) * r.line.quantity, 0))}
                                    </TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell className={styles.sub}>{s("Delivery")}</TableCell>
                                    <TableCell />
                                    {invitations.map(inv => (
                                        <TableCell key={inv.id} className={`${styles.num} ${styles.sub}`}>
                                            {inv.deliveryDays !== undefined ? s("Days").replace("{0}", String(inv.deliveryDays)) : ""}
                                        </TableCell>
                                    ))}
                                    <TableCell className={styles.bestColumn} />
                                </TableRow>
                                {canAward && (
                                    <TableRow>
                                        <TableCell />
                                        <TableCell />
                                        {invitations.map(inv => (
                                            <TableCell key={inv.id} className={styles.num}>
                                                {inv.status === INVITATION_RESPONDED && (
                                                    <Button size="small" appearance={c.totals.find(t => t.invitation.id === inv.id)?.best ? "primary" : "secondary"}
                                                        onClick={() => setAward(inv)}>{s("Award")}</Button>
                                                )}
                                            </TableCell>
                                        ))}
                                        <TableCell className={styles.bestColumn} />
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </div>
                )}
                <Dialog open={!!award} onOpenChange={(_, d) => { if (!d.open) setAward(undefined); }}>
                    <DialogSurface>
                        <DialogBody>
                            <DialogTitle>{s("Award")}</DialogTitle>
                            <DialogContent>{s("Award_Confirm").replace("{0}", award?.name ?? "")}</DialogContent>
                            <DialogActions>
                                <Button appearance="secondary" onClick={() => setAward(undefined)} disabled={busy}>{s("Cancel")}</Button>
                                <Button appearance="primary" onClick={() => void doAward()} disabled={busy}>
                                    {busy ? <Spinner size="tiny" /> : s("Award")}
                                </Button>
                            </DialogActions>
                        </DialogBody>
                    </DialogSurface>
                </Dialog>
            </div>
        </FluentProvider>
    );
}
