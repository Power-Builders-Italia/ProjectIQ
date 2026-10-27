import * as React from "react";
import {
    Button, Checkbox, Dialog, DialogActions, DialogBody, DialogContent, DialogSurface, DialogTitle, Field, FluentProvider,
    MessageBar, MessageBarBody, Spinner, Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Textarea,
    Toolbar, ToolbarButton, makeStyles, tokens, webLightTheme, Theme,
} from "@fluentui/react-components";
import { IInputs } from "./generated/ManifestTypes";
import { fromDay, userLocale } from "../shared/dates";
import { ApprovalGroup, groupForApproval, PendingEntry, selectedIds } from "../shared/approval";
import { callAction, loadPending } from "../shared/execution";
import { CheckmarkIcon, ChevronDownIcon, ChevronRightIcon, DismissIcon, RefreshIcon } from "../shared/icons";

const useStyles = makeStyles({
    root: { display: "flex", flexDirection: "column", gap: tokens.spacingVerticalS, width: "100%" },
    toolbarRight: { marginLeft: "auto", display: "flex", alignItems: "center", gap: tokens.spacingHorizontalS },
    group: { backgroundColor: tokens.colorNeutralBackground2, fontWeight: tokens.fontWeightSemibold },
    num: { textAlign: "right" },
    projects: { color: tokens.colorNeutralForeground3, fontSize: tokens.fontSizeBase200, fontWeight: tokens.fontWeightRegular },
    toggle: { minWidth: "auto" },
    check: { width: "44px" },
    sub: { color: tokens.colorNeutralForeground3, fontSize: tokens.fontSizeBase200 },
});

interface Props {
    context: ComponentFramework.Context<IInputs>;
    refreshKey: number;
}

export function TimeApprovalApp({ context, refreshKey }: Props): React.ReactElement {
    const styles = useStyles();
    const s = (key: string): string => context.resources.getString(key);
    const theme = (context as unknown as { fluentDesignLanguage?: { tokenTheme?: Theme } }).fluentDesignLanguage?.tokenTheme ?? webLightTheme;
    // dashboards host the control in a shrink-to-fit box: take the width the platform allocates
    const width = context.mode.allocatedWidth;
    const fill: React.CSSProperties = { width: width > 0 ? `${width}px` : "100%" };

    const [entries, setEntries] = React.useState<PendingEntry[]>([]);
    const [groupSel, setGroupSel] = React.useState<Set<string>>(new Set());
    const [entrySel, setEntrySel] = React.useState<Set<string>>(new Set());
    const [open, setOpen] = React.useState<Set<string>>(new Set());
    const [loading, setLoading] = React.useState(true);
    const [busy, setBusy] = React.useState(false);
    const [error, setError] = React.useState<string>();
    const [info, setInfo] = React.useState<string>();
    const [rejecting, setRejecting] = React.useState(false);
    const [note, setNote] = React.useState("");
    const [reload, setReload] = React.useState(0);

    React.useEffect(() => {
        let cancelled = false;
        const load = async (): Promise<void> => {
            setLoading(true);
            try {
                const list = await loadPending(context.webAPI);
                if (cancelled) return;
                setEntries(list);
                setGroupSel(new Set());
                setEntrySel(new Set());
                setError(undefined);
            } catch (e) {
                if (!cancelled) setError(`${s("Error_Load")}: ${(e as Error).message}`);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        void load();
        return () => { cancelled = true; };
    }, [refreshKey, reload]);

    const groups = React.useMemo(() => groupForApproval(entries), [entries]);
    const ids = selectedIds(groups, groupSel, entrySel);

    const decide = async (approve: boolean): Promise<void> => {
        setBusy(true);
        setInfo(undefined);
        try {
            const result = await callAction("op365_DecideTimeEntries", approve ? { TimeEntryIds: ids, Approve: true } : { TimeEntryIds: ids, Approve: false, Note: note });
            setInfo(s(approve ? "Approved" : "Rejected").replace("{0}", String(typeof result.Count === "number" ? result.Count : ids.length)));
            setError(undefined);
            setRejecting(false);
            setNote("");
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setBusy(false);
            setReload(r => r + 1);
        }
    };

    const toggle = (set: Set<string>, key: string, update: (s: Set<string>) => void): void => {
        const next = new Set(set);
        if (next.has(key)) next.delete(key); else next.add(key);
        update(next);
    };
    const day = (d: number, opts: Intl.DateTimeFormatOptions): string => fromDay(d).toLocaleDateString(userLocale(context.userSettings.languageId), { timeZone: "UTC", ...opts });
    const hours = (h: number): string => context.formatting.formatDecimal(h, 2).replace(/[.,]00$/, "");
    const allSelected = groups.length > 0 && groups.every(g => groupSel.has(g.key));

    const groupRows = (g: ApprovalGroup): React.ReactElement[] => {
        const expanded = open.has(g.key);
        const rows = [
            <TableRow key={g.key} className={styles.group}>
                <TableCell className={styles.check}>
                    <Checkbox checked={groupSel.has(g.key)} aria-label={g.resourceName} onChange={() => toggle(groupSel, g.key, setGroupSel)} />
                </TableCell>
                <TableCell>
                    <Button className={styles.toggle} appearance="transparent" size="small" icon={expanded ? <ChevronDownIcon /> : <ChevronRightIcon />}
                        aria-label={s(expanded ? "Collapse" : "Expand")} onClick={() => toggle(open, g.key, setOpen)} />
                    {g.resourceName}
                </TableCell>
                <TableCell>
                    {day(g.weekStart, { day: "numeric", month: "short" })} – {day(g.weekStart + 6, { day: "numeric", month: "short", year: "numeric" })}
                    <div className={styles.projects}>{g.projects.map(p => `${p.name} ${hours(p.hours)}`).join(" · ")}</div>
                </TableCell>
                <TableCell className={styles.num}>{hours(g.hours)}</TableCell>
            </TableRow>,
        ];
        if (expanded) {
            g.entries.forEach(e => rows.push(
                <TableRow key={e.id}>
                    <TableCell className={styles.check}>
                        <Checkbox checked={groupSel.has(g.key) || entrySel.has(e.id)} disabled={groupSel.has(g.key)} aria-label={e.projectName}
                            onChange={() => toggle(entrySel, e.id, setEntrySel)} />
                    </TableCell>
                    <TableCell>{day(e.day, { weekday: "short", day: "numeric", month: "short" })}</TableCell>
                    <TableCell>
                        {e.projectName}{e.nodeName ? ` · ${e.nodeName}` : ""}
                        {e.notes && <div className={styles.sub}>{e.notes}</div>}
                    </TableCell>
                    <TableCell className={styles.num}>{hours(e.hours)}</TableCell>
                </TableRow>,
            ));
        }
        return rows;
    };

    return (
        <FluentProvider theme={theme} style={fill}>
            <div className={styles.root}>
                <Toolbar size="small">
                    <ToolbarButton icon={<RefreshIcon />} onClick={() => setReload(r => r + 1)}>{s("Refresh")}</ToolbarButton>
                    <div className={styles.toolbarRight}>
                        {(loading || busy) && <Spinner size="tiny" />}
                        <Button icon={<DismissIcon />} disabled={busy || !ids.length} onClick={() => setRejecting(true)}>{s("Reject")}</Button>
                        <Button appearance="primary" icon={<CheckmarkIcon />} disabled={busy || !ids.length} onClick={() => { void decide(true); }}>
                            {s("Approve")}{ids.length ? ` (${ids.length})` : ""}
                        </Button>
                    </div>
                </Toolbar>
                {error && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>}
                {info && <MessageBar intent="success"><MessageBarBody>{info}</MessageBarBody></MessageBar>}
                {!loading && !groups.length
                    ? <MessageBar><MessageBarBody>{s("Nothing_To_Approve")}</MessageBarBody></MessageBar>
                    : (
                        <Table size="small" aria-label={s("Control_Name")}>
                            <TableHeader>
                                <TableRow>
                                    <TableHeaderCell className={styles.check}>
                                        <Checkbox checked={allSelected} aria-label={s("Select_All")}
                                            onChange={() => setGroupSel(allSelected ? new Set() : new Set(groups.map(g => g.key)))} />
                                    </TableHeaderCell>
                                    <TableHeaderCell>{s("Column_Resource")}</TableHeaderCell>
                                    <TableHeaderCell>{s("Column_Week")}</TableHeaderCell>
                                    <TableHeaderCell className={styles.num}>{s("Column_Hours")}</TableHeaderCell>
                                </TableRow>
                            </TableHeader>
                            <TableBody>{groups.flatMap(groupRows)}</TableBody>
                        </Table>
                    )}
                <Dialog open={rejecting} onOpenChange={(_, d) => setRejecting(d.open)}>
                    <DialogSurface>
                        <DialogBody>
                            <DialogTitle>{s("Reject_Title").replace("{0}", String(ids.length))}</DialogTitle>
                            <DialogContent>
                                <Field label={s("Reject_Note")} required>
                                    <Textarea value={note} onChange={(_, d) => setNote(d.value)} resize="vertical" />
                                </Field>
                            </DialogContent>
                            <DialogActions>
                                <Button onClick={() => setRejecting(false)}>{s("Cancel")}</Button>
                                <Button appearance="primary" disabled={busy || !note.trim()} onClick={() => { void decide(false); }}>{s("Reject")}</Button>
                            </DialogActions>
                        </DialogBody>
                    </DialogSurface>
                </Dialog>
            </div>
        </FluentProvider>
    );
}
