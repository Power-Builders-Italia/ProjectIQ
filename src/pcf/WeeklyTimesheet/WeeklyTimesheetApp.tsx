import * as React from "react";
import {
    Badge, Button, Dropdown, FluentProvider, MessageBar, MessageBarBody, Option, Spinner, Table, TableBody, TableCell,
    TableHeader, TableHeaderCell, TableRow, Toolbar, ToolbarButton, ToolbarDivider, Tooltip, makeStyles, tokens,
    webLightTheme, Theme,
} from "@fluentui/react-components";
import { IInputs } from "./generated/ManifestTypes";
import { EditableCell } from "../shared/EditableCell";
import { fromDay, toDay, userLocale } from "../shared/dates";
import {
    buildTimesheet, Cell, cellChange, cellEditable, parseHours, STATUS, submittable, TimeEntry, TimesheetRow, weekStart,
} from "../shared/timesheet";
import {
    callAction, Choice, createEntry, deleteEntry, loadMe, loadOpenProjects, loadProjectNodes, loadWeek, Me, updateEntry,
} from "../shared/execution";
import { AddIcon, ChevronLeftIcon, ChevronRightIcon, RefreshIcon, SendIcon } from "../shared/icons";

const useStyles = makeStyles({
    root: { display: "flex", flexDirection: "column", gap: tokens.spacingVerticalS, width: "100%" },
    toolbarRight: { marginLeft: "auto", display: "flex", alignItems: "center", gap: tokens.spacingHorizontalS },
    week: { fontWeight: tokens.fontWeightSemibold, minWidth: "180px", textAlign: "center" },
    addLine: { display: "flex", gap: tokens.spacingHorizontalS, alignItems: "center", flexWrap: "wrap" },
    table: { tableLayout: "fixed" },
    first: { width: "34%" },
    day: { textAlign: "right" },
    weekend: { backgroundColor: tokens.colorNeutralBackground3 },
    today: { color: tokens.colorBrandForeground1, fontWeight: tokens.fontWeightSemibold },
    total: { textAlign: "right", fontWeight: tokens.fontWeightSemibold },
    line: { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
    node: { color: tokens.colorNeutralForeground3, fontSize: tokens.fontSizeBase200 },
    over: { color: tokens.colorPaletteRedForeground1 },
    legend: { display: "flex", gap: tokens.spacingHorizontalS, flexWrap: "wrap" },
});

const STATUS_BADGE: Record<number, { key: string; color: "informative" | "warning" | "success" | "danger" }> = {
    [STATUS.draft]: { key: "Status_Draft", color: "informative" },
    [STATUS.submitted]: { key: "Status_Submitted", color: "warning" },
    [STATUS.approved]: { key: "Status_Approved", color: "success" },
    [STATUS.rejected]: { key: "Status_Rejected", color: "danger" },
};

interface Props {
    context: ComponentFramework.Context<IInputs>;
    refreshKey: number;
}

export function WeeklyTimesheetApp({ context, refreshKey }: Props): React.ReactElement {
    const styles = useStyles();
    const s = (key: string): string => context.resources.getString(key);
    const theme = (context as unknown as { fluentDesignLanguage?: { tokenTheme?: Theme } }).fluentDesignLanguage?.tokenTheme ?? webLightTheme;
    // dashboards host the control in a shrink-to-fit box: take the width the platform allocates
    const width = context.mode.allocatedWidth;
    const fill: React.CSSProperties = { width: width > 0 ? `${width}px` : "100%" };
    const today = toDay(new Date())!;

    const [monday, setMonday] = React.useState(weekStart(today));
    const [me, setMe] = React.useState<Me>();
    const [entries, setEntries] = React.useState<TimeEntry[]>([]);
    const [extra, setExtra] = React.useState<Omit<TimesheetRow, "cells" | "total" | "key">[]>([]);
    const [projects, setProjects] = React.useState<Choice[]>([]);
    const [nodes, setNodes] = React.useState<Choice[]>([]);
    const [newProject, setNewProject] = React.useState<Choice>();
    const [newNode, setNewNode] = React.useState<Choice>();
    const [loading, setLoading] = React.useState(true);
    const [busy, setBusy] = React.useState(false);
    const [error, setError] = React.useState<string>();
    const [info, setInfo] = React.useState<string>();
    const [reload, setReload] = React.useState(0);

    React.useEffect(() => {
        let cancelled = false;
        const load = async (): Promise<void> => {
            try {
                const [who, open] = await Promise.all([loadMe(context.webAPI, context.userSettings.userId), loadOpenProjects(context.webAPI)]);
                if (cancelled) return;
                setMe(who);
                setProjects(open);
            } catch (e) {
                if (!cancelled) setError(`${s("Error_Load")}: ${(e as Error).message}`);
            }
        };
        void load();
        return () => { cancelled = true; };
    }, []);

    React.useEffect(() => {
        if (!me) return;
        if (!me.resourceId) { setLoading(false); return; }
        let cancelled = false;
        const load = async (): Promise<void> => {
            setLoading(true);
            try {
                const week = await loadWeek(context.webAPI, me.resourceId!, monday);
                if (cancelled) return;
                setEntries(week);
                setError(undefined);
            } catch (e) {
                if (!cancelled) setError(`${s("Error_Load")}: ${(e as Error).message}`);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        void load();
        return () => { cancelled = true; };
    }, [me, monday, refreshKey, reload]);

    React.useEffect(() => {
        setNewNode(undefined);
        if (!newProject) { setNodes([]); return; }
        let cancelled = false;
        const load = async (): Promise<void> => {
            try {
                const list = await loadProjectNodes(context.webAPI, newProject.id);
                if (!cancelled) setNodes(list);
            } catch (e) {
                if (!cancelled) setError(`${s("Error_Load")}: ${(e as Error).message}`);
            }
        };
        void load();
        return () => { cancelled = true; };
    }, [newProject]);

    const run = async (work: () => Promise<void>, done?: string): Promise<void> => {
        setBusy(true);
        setInfo(undefined);
        try {
            await work();
            setError(undefined);
            if (done) setInfo(done);
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setBusy(false);
            setReload(r => r + 1);
        }
    };

    const commit = (row: TimesheetRow, dayIndex: number, text: string): void => {
        const hours = parseHours(text);
        if (hours === undefined) { setError(s("Error_Hours")); return; }
        const change = cellChange(row, dayIndex, hours);
        if (change.kind === "none") return;
        void run(async () => {
            if (change.kind === "create") await createEntry(context.webAPI, change.projectId, change.nodeId, monday + change.dayIndex, change.hours);
            if (change.kind === "update") await updateEntry(context.webAPI, change.id, change.hours);
            if (change.kind === "delete") await deleteEntry(context.webAPI, change.id);
        });
    };

    const sheet = buildTimesheet(entries, monday, extra);
    const toSubmit = submittable(sheet);
    const submit = (): void => {
        void run(async () => {
            const result = await callAction("op365_SubmitTimeEntries", { TimeEntryIds: toSubmit });
            setInfo(s("Submitted").replace("{0}", String(typeof result.Count === "number" ? result.Count : toSubmit.length)));
        });
    };
    const addLine = (): void => {
        if (!newProject) return;
        setExtra(x => [...x, { projectId: newProject.id, projectName: newProject.name, nodeId: newNode?.id, nodeName: newNode?.name }]);
        setNewProject(undefined);
    };

    const fmtDay = (day: number, opts: Intl.DateTimeFormatOptions): string =>
        fromDay(day).toLocaleDateString(userLocale(context.userSettings.languageId), { timeZone: "UTC", ...opts });
    const hours = (h: number): string => (h ? context.formatting.formatDecimal(h, 2).replace(/[.,]00$/, "") : "");

    if (me && !me.resourceId) {
        return <FluentProvider theme={theme} style={fill}><MessageBar intent="warning"><MessageBarBody>{s("No_Resource")}</MessageBarBody></MessageBar></FluentProvider>;
    }

    const cell = (row: TimesheetRow, c: Cell, i: number): React.ReactElement => {
        const status = c.entries.length === 1 ? c.entries[0].status : undefined;
        const badge = status !== undefined && status !== STATUS.draft ? STATUS_BADGE[status] : undefined;
        const value = hours(c.hours);
        const content = cellEditable(c) && !busy
            ? <EditableCell display={value} value={c.hours ? String(c.hours) : ""} type="number" min={0} max={24}
                ariaLabel={`${row.projectName} ${fmtDay(monday + i, { weekday: "long" })}`} onCommit={v => commit(row, i, v)} />
            : <span>{value}</span>;
        return (
            <TableCell key={i} className={`${styles.day} ${i >= 5 ? styles.weekend : ""}`}>
                {badge ? <Tooltip content={s(badge.key)} relationship="description"><Badge appearance="tint" color={badge.color}>{content}</Badge></Tooltip> : content}
            </TableCell>
        );
    };

    return (
        <FluentProvider theme={theme} style={fill}>
            <div className={styles.root}>
                <Toolbar size="small">
                    <ToolbarButton icon={<ChevronLeftIcon />} aria-label={s("Previous_Week")} onClick={() => setMonday(m => m - 7)} />
                    <span className={styles.week}>{fmtDay(monday, { day: "numeric", month: "short" })} – {fmtDay(monday + 6, { day: "numeric", month: "short", year: "numeric" })}</span>
                    <ToolbarButton icon={<ChevronRightIcon />} aria-label={s("Next_Week")} onClick={() => setMonday(m => m + 7)} />
                    <ToolbarButton onClick={() => setMonday(weekStart(today))}>{s("This_Week")}</ToolbarButton>
                    <ToolbarDivider />
                    <ToolbarButton icon={<RefreshIcon />} onClick={() => setReload(r => r + 1)}>{s("Refresh")}</ToolbarButton>
                    <div className={styles.toolbarRight}>
                        {(loading || busy) && <Spinner size="tiny" />}
                        <Button appearance="primary" icon={<SendIcon />} disabled={busy || !toSubmit.length} onClick={submit}>
                            {s("Submit_Week")}{toSubmit.length ? ` (${toSubmit.length})` : ""}
                        </Button>
                    </div>
                </Toolbar>
                {error && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>}
                {info && <MessageBar intent="success"><MessageBarBody>{info}</MessageBarBody></MessageBar>}
                <Table size="small" className={styles.table} aria-label={s("Control_Name")}>
                    <TableHeader>
                        <TableRow>
                            <TableHeaderCell className={styles.first}>{s("Column_Line")}</TableHeaderCell>
                            {[0, 1, 2, 3, 4, 5, 6].map(i => (
                                <TableHeaderCell key={i} className={`${i >= 5 ? styles.weekend : ""}`}>
                                    <span className={monday + i === today ? styles.today : undefined}>
                                        {fmtDay(monday + i, { weekday: "short", day: "numeric" })}
                                    </span>
                                </TableHeaderCell>
                            ))}
                            <TableHeaderCell>{s("Column_Total")}</TableHeaderCell>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {sheet.rows.map(row => (
                            <TableRow key={row.key}>
                                <TableCell>
                                    <div className={styles.line} title={row.projectName}>{row.projectName}</div>
                                    {row.nodeName && <div className={`${styles.line} ${styles.node}`} title={row.nodeName}>{row.nodeName}</div>}
                                </TableCell>
                                {row.cells.map((c, i) => cell(row, c, i))}
                                <TableCell className={styles.total}>{hours(row.total)}</TableCell>
                            </TableRow>
                        ))}
                        <TableRow>
                            <TableCell className={styles.total}>{s("Column_Total")}</TableCell>
                            {sheet.dayTotals.map((t, i) => (
                                <TableCell key={i} className={`${styles.total} ${i >= 5 ? styles.weekend : ""} ${t > 24 ? styles.over : ""}`}>{hours(t)}</TableCell>
                            ))}
                            <TableCell className={`${styles.total} ${me && sheet.total > me.weeklyHours ? styles.over : ""}`}>
                                <Tooltip content={`${s("Capacity")}: ${me?.weeklyHours ?? 0}`} relationship="description"><span>{hours(sheet.total) || "0"}</span></Tooltip>
                            </TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
                <div className={styles.addLine}>
                    <Dropdown placeholder={s("Pick_Project")} value={newProject?.name ?? ""} selectedOptions={newProject ? [newProject.id] : []}
                        onOptionSelect={(_, d) => setNewProject(projects.find(p => p.id === d.optionValue))}>
                        {projects.map(p => <Option key={p.id} value={p.id}>{p.name}</Option>)}
                    </Dropdown>
                    <Dropdown placeholder={s("Pick_Task")} disabled={!nodes.length} value={newNode?.name ?? ""} selectedOptions={newNode ? [newNode.id] : []}
                        onOptionSelect={(_, d) => setNewNode(nodes.find(n => n.id === d.optionValue))}>
                        {nodes.map(n => <Option key={n.id} value={n.id}>{n.name}</Option>)}
                    </Dropdown>
                    <Button icon={<AddIcon />} disabled={!newProject} onClick={addLine}>{s("Add_Line")}</Button>
                    <div className={styles.toolbarRight}>
                        <div className={styles.legend}>
                            {[STATUS.submitted, STATUS.approved, STATUS.rejected].map(st => (
                                <Badge key={st} appearance="tint" color={STATUS_BADGE[st].color}>{s(STATUS_BADGE[st].key)}</Badge>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </FluentProvider>
    );
}
