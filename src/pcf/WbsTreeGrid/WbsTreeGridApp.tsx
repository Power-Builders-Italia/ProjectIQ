import * as React from "react";
import {
    Button, FluentProvider, MessageBar, MessageBarBody, Spinner, Table, TableBody, TableCell, TableHeader,
    TableHeaderCell, TableRow, Toolbar, ToolbarButton, Tooltip, makeStyles, tokens, webLightTheme, Theme,
} from "@fluentui/react-components";
import { AddIcon, ChevronDownIcon, ChevronRightIcon, CollapseIcon, ExpandIcon, RefreshIcon } from "../shared/icons";
import { IInputs } from "./generated/ManifestTypes";
import { buildTree, flatten, parentIds, WbsNode } from "../shared/wbs";
import { currencySymbol, hostRecordId, loadNodes, updateNode } from "../shared/data";
import { isoDay, toDay } from "../shared/dates";
import { EditableCell } from "../shared/EditableCell";
import { ProgressCell } from "../shared/ProgressCell";
import { progressLabel } from "../shared/progress";

const useStyles = makeStyles({
    root: { display: "flex", flexDirection: "column", gap: tokens.spacingVerticalS, width: "100%" },
    scroller: { overflowX: "auto" },
    table: { minWidth: "1000px" },
    name: { display: "flex", alignItems: "center", gap: tokens.spacingHorizontalXS },
    link: { cursor: "pointer", color: tokens.colorBrandForeground1, ":hover": { textDecorationLine: "underline" } },
    parent: { fontWeight: tokens.fontWeightSemibold },
    rolled: { color: tokens.colorNeutralForeground2, fontStyle: "italic" },
    num: { textAlign: "right" },
    progress: { minWidth: "160px" },
    selected: { backgroundColor: tokens.colorNeutralBackground1Selected },
    total: { fontWeight: tokens.fontWeightSemibold, borderTop: `2px solid ${tokens.colorNeutralStroke1}` },
    spacer: { width: "24px", display: "inline-block" },
});

interface Props {
    context: ComponentFramework.Context<IInputs>;
    refreshKey: number;
}

type NumberField = "op365_budgethours" | "op365_budgetlabour" | "op365_budgetmaterials" | "op365_budgetother" | "op365_progresspct";

export function WbsTreeGridApp({ context, refreshKey }: Props): React.ReactElement {
    const styles = useStyles();
    const s = (key: string): string => context.resources.getString(key);
    const projectId = hostRecordId(context);
    const theme = (context as unknown as { fluentDesignLanguage?: { tokenTheme?: Theme } }).fluentDesignLanguage?.tokenTheme ?? webLightTheme;

    const [roots, setRoots] = React.useState<WbsNode[]>([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string>();
    const [collapsed, setCollapsed] = React.useState<Set<string>>(new Set());
    const [selected, setSelected] = React.useState<string>();
    const [reload, setReload] = React.useState(0);
    const [symbol, setSymbol] = React.useState<string>();

    React.useEffect(() => {
        if (!projectId) { setLoading(false); return; }
        let cancelled = false;
        const load = async (): Promise<void> => {
            setLoading(true);
            try {
                const [items, sym] = await Promise.all([loadNodes(context.webAPI, projectId), currencySymbol(context.webAPI, "op365_project", projectId)]);
                if (!cancelled) { setRoots(buildTree(items)); setSymbol(sym); setError(undefined); }
            } catch (e) {
                if (!cancelled) setError(`${s("Error_Load")}: ${(e as Error).message}`);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        void load();
        return () => { cancelled = true; };
    }, [projectId, refreshKey, reload]);

    // amounts in the project currency (#33)
    const money = (v: number): string => context.formatting.formatCurrency(v, 2, symbol);
    const decimal = (v: number): string => context.formatting.formatDecimal(v, 2);
    const date = (d?: number): string => (d === undefined ? "" : context.formatting.formatDateShort(new Date(isoDay(d) + "T12:00:00")));

    const save = async (id: string, values: Record<string, unknown>): Promise<void> => {
        try {
            await updateNode(context.webAPI, id, values);
            setReload(r => r + 1);
            context.parameters.nodes.refresh();
        } catch (e) {
            setError(`${s("Error_Save")}: ${(e as Error).message}`);
        }
    };
    const saveNumber = (id: string, field: NumberField, raw: string): void => {
        const v = raw.trim() === "" ? null : Number(raw);
        if (v !== null && (isNaN(v) || v < 0 || (field === "op365_progresspct" && v > 100))) return;
        void save(id, { [field]: v });
    };
    const saveDate = (id: string, field: "op365_startdate" | "op365_enddate", raw: string): void => {
        void save(id, { [field]: raw ? isoDay(toDay(raw)!) : null });
    };

    const openNode = async (id: string): Promise<void> => {
        await context.navigation.openForm({ entityName: "op365_wbsnode", entityId: id });
        setReload(r => r + 1);
    };
    const newNode = async (parent?: WbsNode): Promise<void> => {
        if (!projectId) return;
        const project = await context.webAPI.retrieveRecord("op365_project", projectId, "?$select=op365_name");
        const params: Record<string, string> = {
            op365_projectid: projectId, op365_projectidname: project.op365_name as string, op365_projectidtype: "op365_project",
        };
        if (parent) {
            params.op365_parentid = parent.id;
            params.op365_parentidname = parent.name;
            params.op365_parentidtype = "op365_wbsnode";
        }
        await context.navigation.openForm({ entityName: "op365_wbsnode" }, params);
        setReload(r => r + 1);
        context.parameters.nodes.refresh();
    };

    const toggle = (id: string): void => {
        const next = new Set(collapsed);
        if (next.has(id)) next.delete(id); else next.add(id);
        setCollapsed(next);
    };

    if (!projectId) {
        return <FluentProvider theme={theme}><MessageBar><MessageBarBody>{s("Save_Project")}</MessageBarBody></MessageBar></FluentProvider>;
    }

    const rows = flatten(roots, collapsed);
    const selectedNode = rows.find(r => r.id === selected);
    const totalHours = roots.reduce((t, r) => t + r.totalHours, 0);
    const totalBudget = roots.reduce((t, r) => t + r.totalBudget, 0);
    const disabled = context.mode.isControlDisabled;

    const numberCell = (n: WbsNode, field: NumberField, value: number, label: string, format: (v: number) => string): React.ReactElement => (
        <EditableCell type="number" min={0} max={field === "op365_progresspct" ? 100 : undefined} disabled={disabled}
            display={format(value)} value={String(value)} ariaLabel={`${label} ${n.name}`}
            onCommit={v => saveNumber(n.id, field, v)} />
    );

    return (
        <FluentProvider theme={theme} className={styles.root}>
            <Toolbar size="small">
                <ToolbarButton icon={<AddIcon />} disabled={disabled} onClick={() => void newNode()}>{s("Add_Node")}</ToolbarButton>
                <ToolbarButton icon={<AddIcon />} disabled={disabled || !selectedNode} onClick={() => void newNode(selectedNode)}>{s("Add_Child")}</ToolbarButton>
                <ToolbarButton icon={<ExpandIcon />} onClick={() => setCollapsed(new Set())}>{s("Expand_All")}</ToolbarButton>
                <ToolbarButton icon={<CollapseIcon />} onClick={() => setCollapsed(new Set(parentIds(roots)))}>{s("Collapse_All")}</ToolbarButton>
                <ToolbarButton icon={<RefreshIcon />} onClick={() => setReload(r => r + 1)}>{s("Refresh")}</ToolbarButton>
                {loading && <Spinner size="tiny" />}
            </Toolbar>
            {error && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>}
            {!loading && !rows.length && !error && <MessageBar><MessageBarBody>{s("Empty")}</MessageBarBody></MessageBar>}
            {rows.length > 0 && (
                <div className={styles.scroller}>
                    <Table size="small" className={styles.table} aria-label={s("Control_Name")}>
                        <TableHeader>
                            <TableRow>
                                <TableHeaderCell style={{ width: "34%" }}>{s("Col_Name")}</TableHeaderCell>
                                <TableHeaderCell>{s("Col_Start")}</TableHeaderCell>
                                <TableHeaderCell>{s("Col_End")}</TableHeaderCell>
                                <TableHeaderCell className={styles.num}>{s("Col_Hours")}</TableHeaderCell>
                                <TableHeaderCell className={styles.num}>{s("Col_Labour")}</TableHeaderCell>
                                <TableHeaderCell className={styles.num}>{s("Col_Materials")}</TableHeaderCell>
                                <TableHeaderCell className={styles.num}>{s("Col_Other")}</TableHeaderCell>
                                <TableHeaderCell className={styles.num}>{s("Col_Total")}</TableHeaderCell>
                                <TableHeaderCell className={styles.progress}>{s("Col_Progress")}</TableHeaderCell>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map(n => {
                                const isParent = n.children.length > 0;
                                const rolled = (text: string): React.ReactElement => (
                                    <Tooltip content={s("Rolled_Up")} relationship="description"><span className={styles.rolled}>{text}</span></Tooltip>
                                );
                                return (
                                    <TableRow key={n.id} className={n.id === selected ? styles.selected : undefined} onClick={() => setSelected(n.id)}>
                                        <TableCell>
                                            <div className={styles.name} style={{ paddingLeft: `${n.level * 20}px` }}>
                                                {isParent
                                                    ? <Button size="small" appearance="transparent" aria-expanded={!collapsed.has(n.id)}
                                                        icon={collapsed.has(n.id) ? <ChevronRightIcon /> : <ChevronDownIcon />}
                                                        onClick={e => { e.stopPropagation(); toggle(n.id); }} />
                                                    : <span className={styles.spacer} />}
                                                <span className={`${styles.link} ${isParent ? styles.parent : ""}`} role="link" tabIndex={0}
                                                    onClick={() => void openNode(n.id)} onKeyDown={e => { if (e.key === "Enter") void openNode(n.id); }}>
                                                    {n.code ? `${n.code} ${n.name}` : n.name}
                                                </span>
                                            </div>
                                        </TableCell>
                                        {isParent ? <>
                                            <TableCell>{rolled(date(n.rollStart))}</TableCell>
                                            <TableCell>{rolled(date(n.rollEnd))}</TableCell>
                                            <TableCell className={styles.num}>{rolled(decimal(n.totalHours))}</TableCell>
                                            <TableCell /><TableCell /><TableCell />
                                            <TableCell className={styles.num}>{rolled(money(n.totalBudget))}</TableCell>
                                            <TableCell><ProgressCell pct={n.rollProgress} label={rolled(progressLabel(n.rollProgress))} /></TableCell>
                                        </> : <>
                                            <TableCell>
                                                <EditableCell type="date" disabled={disabled} display={date(n.start)} value={n.start === undefined ? "" : isoDay(n.start)}
                                                    ariaLabel={`${s("Col_Start")} ${n.name}`} onCommit={v => saveDate(n.id, "op365_startdate", v)} />
                                            </TableCell>
                                            <TableCell>
                                                <EditableCell type="date" disabled={disabled} display={date(n.end)} value={n.end === undefined ? "" : isoDay(n.end)}
                                                    ariaLabel={`${s("Col_End")} ${n.name}`} onCommit={v => saveDate(n.id, "op365_enddate", v)} />
                                            </TableCell>
                                            <TableCell className={styles.num}>{numberCell(n, "op365_budgethours", n.budgetHours, s("Col_Hours"), decimal)}</TableCell>
                                            <TableCell className={styles.num}>{numberCell(n, "op365_budgetlabour", n.budgetLabour, s("Col_Labour"), money)}</TableCell>
                                            <TableCell className={styles.num}>{numberCell(n, "op365_budgetmaterials", n.budgetMaterials, s("Col_Materials"), money)}</TableCell>
                                            <TableCell className={styles.num}>{numberCell(n, "op365_budgetother", n.budgetOther, s("Col_Other"), money)}</TableCell>
                                            <TableCell className={styles.num}>{money(n.totalBudget)}</TableCell>
                                            <TableCell><ProgressCell pct={n.progress} label={numberCell(n, "op365_progresspct", n.progress, s("Col_Progress"), progressLabel)} /></TableCell>
                                        </>}
                                    </TableRow>
                                );
                            })}
                            <TableRow className={styles.total}>
                                <TableCell>{s("Totals")}</TableCell>
                                <TableCell /><TableCell />
                                <TableCell className={styles.num}>{decimal(totalHours)}</TableCell>
                                <TableCell /><TableCell /><TableCell />
                                <TableCell className={styles.num}>{money(totalBudget)}</TableCell>
                                <TableCell />
                            </TableRow>
                        </TableBody>
                    </Table>
                </div>
            )}
        </FluentProvider>
    );
}
