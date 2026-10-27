import * as React from "react";
import {
    Button, Dropdown, FluentProvider, MessageBar, MessageBarBody, Option, Spinner, Switch, Tab, TabList, Toolbar,
    ToolbarButton, ToolbarDivider, Tooltip, makeStyles, tokens, webLightTheme, Theme,
} from "@fluentui/react-components";
import { IInputs } from "./generated/ManifestTypes";
import { buildTree, flatten, WbsNode } from "../shared/wbs";
import { BaselineBar, BaselineInfo, hostRecordId, loadBaselineBars, loadBaselines, loadLinks, loadNodes } from "../shared/data";
import { CpmLink, criticalPath, CpmResult } from "../shared/cpm";
import { isoDay, toDay } from "../shared/dates";
import { bands, PX_PER_DAY, range, Zoom } from "../shared/timeline";
import { ChevronDownIcon, ChevronRightIcon, RefreshIcon } from "../shared/icons";

const ROW = 30, HEADER = 44, LABELS = 280;

const useStyles = makeStyles({
    root: { display: "flex", flexDirection: "column", gap: tokens.spacingVerticalS, width: "100%" },
    chart: { display: "flex", border: `1px solid ${tokens.colorNeutralStroke2}`, borderRadius: tokens.borderRadiusMedium, overflow: "hidden" },
    labels: { width: `${LABELS}px`, flexShrink: 0, borderRight: `1px solid ${tokens.colorNeutralStroke2}`, backgroundColor: tokens.colorNeutralBackground1 },
    labelHeader: { height: `${HEADER}px`, borderBottom: `1px solid ${tokens.colorNeutralStroke2}`, backgroundColor: tokens.colorNeutralBackground2 },
    label: {
        height: `${ROW}px`, display: "flex", alignItems: "center", gap: tokens.spacingHorizontalXS, overflow: "hidden",
        whiteSpace: "nowrap", textOverflow: "ellipsis", fontSize: tokens.fontSizeBase200, paddingRight: tokens.spacingHorizontalS,
    },
    link: { cursor: "pointer", overflow: "hidden", textOverflow: "ellipsis", ":hover": { textDecorationLine: "underline" } },
    parent: { fontWeight: tokens.fontWeightSemibold },
    spacer: { width: "24px", flexShrink: 0 },
    timeline: { overflowX: "auto", flexGrow: 1 },
    toolbarRight: { marginLeft: "auto", display: "flex", alignItems: "center", gap: tokens.spacingHorizontalS },
});

interface Props {
    context: ComponentFramework.Context<IInputs>;
    refreshKey: number;
}

export function GanttChartApp({ context, refreshKey }: Props): React.ReactElement {
    const styles = useStyles();
    const s = (key: string): string => context.resources.getString(key);
    const projectId = hostRecordId(context);
    const theme = (context as unknown as { fluentDesignLanguage?: { tokenTheme?: Theme } }).fluentDesignLanguage?.tokenTheme ?? webLightTheme;

    const [roots, setRoots] = React.useState<WbsNode[]>([]);
    const [links, setLinks] = React.useState<CpmLink[]>([]);
    const [baselines, setBaselines] = React.useState<BaselineInfo[]>([]);
    const [baselineId, setBaselineId] = React.useState<string>("");
    const [baselineBars, setBaselineBars] = React.useState<Map<string, BaselineBar>>(new Map());
    const [zoom, setZoom] = React.useState<Zoom>("month");
    const [showCritical, setShowCritical] = React.useState(true);
    const [collapsed, setCollapsed] = React.useState<Set<string>>(new Set());
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string>();
    const [reload, setReload] = React.useState(0);

    React.useEffect(() => {
        if (!projectId) { setLoading(false); return; }
        let cancelled = false;
        const load = async (): Promise<void> => {
            setLoading(true);
            try {
                const [items, deps, bls] = await Promise.all([
                    loadNodes(context.webAPI, projectId), loadLinks(context.webAPI, projectId), loadBaselines(context.webAPI, projectId)]);
                if (cancelled) return;
                setRoots(buildTree(items));
                setLinks(deps);
                setBaselines(bls);
                setBaselineId(current => (current && bls.some(b => b.id === current) ? current : bls.find(b => b.isReference)?.id ?? ""));
                setError(undefined);
            } catch (e) {
                if (!cancelled) setError(`${s("Error_Load")}: ${(e as Error).message}`);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        void load();
        return () => { cancelled = true; };
    }, [projectId, refreshKey, reload]);

    React.useEffect(() => {
        if (!baselineId) { setBaselineBars(new Map()); return; }
        let cancelled = false;
        const load = async (): Promise<void> => {
            try {
                const bars = await loadBaselineBars(context.webAPI, baselineId);
                if (!cancelled) setBaselineBars(bars);
            } catch (e) {
                if (!cancelled) setError(`${s("Error_Load")}: ${(e as Error).message}`);
            }
        };
        void load();
        return () => { cancelled = true; };
    }, [baselineId]);

    const allNodes = React.useMemo(() => flatten(roots, new Set()), [roots]);
    const cpm: CpmResult = React.useMemo(() => criticalPath(
        allNodes.filter(n => !n.children.length && n.start !== undefined && n.end !== undefined && n.end >= n.start)
            .map(n => ({ id: n.id, start: n.start!, end: n.end! })),
        links), [allNodes, links]);

    if (!projectId) {
        return <FluentProvider theme={theme}><MessageBar><MessageBarBody>{s("Save_Project")}</MessageBarBody></MessageBar></FluentProvider>;
    }

    const rows = flatten(roots, collapsed);
    const days: number[] = [];
    allNodes.forEach(n => {
        [n.rollStart, n.rollEnd, cpm.earlyFinish.get(n.id), baselineBars.get(n.id)?.start, baselineBars.get(n.id)?.end]
            .forEach(d => { if (d !== undefined) days.push(d); });
    });
    const today = toDay(new Date())!;
    const hasDates = days.length > 0;
    const view = range(hasDates ? Math.min(...days) : today, hasDates ? Math.max(...days) : today + 30, zoom);
    const px = PX_PER_DAY[zoom];
    const x = (day: number): number => (day - view.start) * px;
    const width = Math.max(x(view.end + 1), 300);
    const height = HEADER + rows.length * ROW;
    const band = bands(view.start, view.end, zoom);
    const rowIndex = new Map(rows.map((r, i) => [r.id, i]));
    const date = (d?: number): string => (d === undefined ? "" : context.formatting.formatDateShort(new Date(isoDay(d) + "T12:00:00")));
    const critical = (id: string): boolean => showCritical && cpm.critical.has(id);

    const openNode = async (id: string): Promise<void> => {
        await context.navigation.openForm({ entityName: "op365_wbsnode", entityId: id });
        setReload(r => r + 1);
    };
    const toggle = (id: string): void => {
        const next = new Set(collapsed);
        if (next.has(id)) next.delete(id); else next.add(id);
        setCollapsed(next);
    };

    const tooltip = (n: WbsNode): string => {
        const parts = [`${n.code ? n.code + " " : ""}${n.name}`, `${s("Tip_Dates")}: ${date(n.rollStart)} – ${date(n.rollEnd)}`,
            `${s("Tip_Progress")}: ${context.formatting.formatDecimal(n.rollProgress, 0)}%`];
        const es = cpm.earlyStart.get(n.id);
        if (es !== undefined && n.start !== undefined && es > n.start) parts.push(`${s("Tip_Late")} ${date(es)} – ${date(cpm.earlyFinish.get(n.id))}`);
        if (cpm.float.has(n.id)) parts.push(`${s("Tip_Float")}: ${cpm.float.get(n.id)}`);
        if (critical(n.id)) parts.push(s("Tip_Critical"));
        const b = baselineBars.get(n.id);
        if (b?.start !== undefined) parts.push(`${s("Tip_Baseline")}: ${date(b.start)} – ${date(b.end)}`);
        return parts.join("\n");
    };

    const bar = (n: WbsNode, i: number): React.ReactNode => {
        if (n.rollStart === undefined || n.rollEnd === undefined || n.rollEnd < n.rollStart) return null;
        const y = HEADER + i * ROW;
        const x0 = x(n.rollStart), w = Math.max(x(n.rollEnd + 1) - x0, 2);
        const isParent = n.children.length > 0;
        const b = baselineBars.get(n.id);
        const es = cpm.earlyStart.get(n.id), ef = cpm.earlyFinish.get(n.id);
        const pushed = !isParent && es !== undefined && ef !== undefined && n.start !== undefined && es > n.start;
        const fill = isParent ? tokens.colorNeutralForeground2 : critical(n.id) ? tokens.colorPaletteRedBackground3 : tokens.colorBrandBackground;
        const done = isParent ? tokens.colorNeutralForeground1 : critical(n.id) ? tokens.colorPaletteRedForeground1 : tokens.colorBrandBackgroundPressed;
        return (
            <g key={n.id}>
                {b?.start !== undefined && b.end !== undefined && (
                    <rect x={x(b.start)} y={y + ROW - 9} width={Math.max(x(b.end + 1) - x(b.start), 2)} height={4} rx={1}
                        fill={tokens.colorNeutralStrokeAccessible} opacity={0.6} />
                )}
                {pushed && (
                    <rect x={x(es)} y={y + 7} width={Math.max(x(ef + 1) - x(es), 2)} height={ROW - 16} rx={3}
                        fill="none" stroke={fill} strokeDasharray="4 3" />
                )}
                <Tooltip content={<span style={{ whiteSpace: "pre-line" }}>{tooltip(n)}</span>} relationship="description" withArrow>
                    <g style={{ cursor: "pointer" }} onClick={() => void openNode(n.id)}>
                        <rect x={x0} y={y + (isParent ? 10 : 7)} width={w} height={isParent ? 8 : ROW - 16} rx={isParent ? 1 : 3} fill={fill} />
                        <rect x={x0} y={y + (isParent ? 10 : 7)} width={w * Math.min(Math.max(n.rollProgress, 0), 100) / 100}
                            height={isParent ? 8 : ROW - 16} rx={isParent ? 1 : 3} fill={done} />
                    </g>
                </Tooltip>
            </g>
        );
    };

    const arrow = (l: CpmLink, k: number): React.ReactNode => {
        const pi = rowIndex.get(l.predecessorId), si = rowIndex.get(l.successorId);
        const p = rows[pi ?? -1], q = rows[si ?? -1];
        if (!p || !q || p.rollEnd === undefined || q.rollStart === undefined) return null;
        const x1 = x(p.rollEnd + 1), y1 = HEADER + pi! * ROW + ROW / 2;
        const x2 = x(q.rollStart), y2 = HEADER + si! * ROW + ROW / 2;
        const mid = Math.max(x1 + 6, Math.min(x2 - 6, x1 + 12));
        const isCritical = critical(l.predecessorId) && critical(l.successorId);
        const color = isCritical ? tokens.colorPaletteRedForeground1 : tokens.colorNeutralForeground3;
        const d = x2 - 6 >= x1 + 6
            ? `M${x1},${y1} H${mid} V${y2} H${x2 - 1}`
            : `M${x1},${y1} H${x1 + 6} V${y1 + (y2 > y1 ? ROW / 2 : -ROW / 2)} H${x2 - 8} V${y2} H${x2 - 1}`;
        return <path key={k} d={d} fill="none" stroke={color} strokeWidth={1.2} markerEnd={`url(#op365-arrow-${isCritical ? "c" : "n"})`} />;
    };

    return (
        <FluentProvider theme={theme} className={styles.root}>
            <Toolbar size="small">
                <TabList size="small" selectedValue={zoom} onTabSelect={(_, d) => setZoom(d.value as Zoom)}>
                    <Tab value="week">{s("Zoom_Week")}</Tab>
                    <Tab value="month">{s("Zoom_Month")}</Tab>
                    <Tab value="quarter">{s("Zoom_Quarter")}</Tab>
                </TabList>
                <ToolbarDivider />
                <Dropdown size="small" aria-label={s("Baseline")} placeholder={s("Baseline")}
                    value={baselineId ? (baselines.find(b => b.id === baselineId)?.name ?? "") : s("Baseline_None")}
                    selectedOptions={[baselineId]} onOptionSelect={(_, d) => setBaselineId(d.optionValue ?? "")}>
                    <Option value="">{s("Baseline_None")}</Option>
                    {baselines.map(b => (
                        <Option key={b.id} value={b.id} text={b.name}>{b.isReference ? `${b.name} ${s("Baseline_Reference")}` : b.name}</Option>
                    ))}
                </Dropdown>
                <Switch label={s("Critical_Path")} checked={showCritical} onChange={(_, d) => setShowCritical(d.checked)} />
                <div className={styles.toolbarRight}>
                    {loading && <Spinner size="tiny" />}
                    <ToolbarButton icon={<RefreshIcon />} onClick={() => setReload(r => r + 1)}>{s("Refresh")}</ToolbarButton>
                </div>
            </Toolbar>
            {error && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>}
            {cpm.cyclic.size > 0 && <MessageBar intent="warning"><MessageBarBody>{s("Loop_Warning")}</MessageBarBody></MessageBar>}
            {!loading && !hasDates && !error && <MessageBar><MessageBarBody>{s("Empty")}</MessageBarBody></MessageBar>}
            {rows.length > 0 && (
                <div className={styles.chart}>
                    <div className={styles.labels}>
                        <div className={styles.labelHeader} />
                        {rows.map(n => (
                            <div key={n.id} className={styles.label} style={{ paddingLeft: `${n.level * 16}px` }}>
                                {n.children.length
                                    ? <Button size="small" appearance="transparent" aria-expanded={!collapsed.has(n.id)}
                                        icon={collapsed.has(n.id) ? <ChevronRightIcon /> : <ChevronDownIcon />} onClick={() => toggle(n.id)} />
                                    : <span className={styles.spacer} />}
                                <span className={`${styles.link} ${n.children.length ? styles.parent : ""}`} role="link" tabIndex={0}
                                    title={n.name} onClick={() => void openNode(n.id)}
                                    onKeyDown={e => { if (e.key === "Enter") void openNode(n.id); }}>
                                    {n.code ? `${n.code} ${n.name}` : n.name}
                                </span>
                            </div>
                        ))}
                    </div>
                    <div className={styles.timeline}>
                        <svg width={width} height={height} role="img" aria-label={s("Control_Name")} style={{ display: "block" }}>
                            <defs>
                                {(["n", "c"] as const).map(k => (
                                    <marker key={k} id={`op365-arrow-${k}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                                        <path d="M0,0 L8,4 L0,8 Z" fill={k === "c" ? tokens.colorPaletteRedForeground1 : tokens.colorNeutralForeground3} />
                                    </marker>
                                ))}
                            </defs>
                            <rect x={0} y={0} width={width} height={HEADER} fill={tokens.colorNeutralBackground2} />
                            {band.upper.map(b => (
                                <g key={`u${b.start}`}>
                                    <line x1={x(b.start)} x2={x(b.start)} y1={0} y2={HEADER / 2} stroke={tokens.colorNeutralStroke2} />
                                    <text x={x(b.start) + 4} y={15} fontSize={11} fontWeight={600} fill={tokens.colorNeutralForeground2}>{b.label}</text>
                                </g>
                            ))}
                            {band.lower.map(b => (
                                <g key={`l${b.start}`}>
                                    <line x1={x(b.start)} x2={x(b.start)} y1={HEADER / 2} y2={height} stroke={tokens.colorNeutralStroke3} />
                                    <text x={x(b.start) + 3} y={HEADER - 7} fontSize={10} fill={tokens.colorNeutralForeground3}>{b.label}</text>
                                </g>
                            ))}
                            <line x1={0} x2={width} y1={HEADER} y2={HEADER} stroke={tokens.colorNeutralStroke2} />
                            {rows.map((n, i) => i % 2 === 1 && (
                                <rect key={`z${n.id}`} x={0} y={HEADER + i * ROW} width={width} height={ROW} fill={tokens.colorNeutralBackground1Hover} opacity={0.4} />
                            ))}
                            {today >= view.start && today <= view.end && (
                                <g>
                                    <line x1={x(today) + px / 2} x2={x(today) + px / 2} y1={HEADER} y2={height} stroke={tokens.colorPaletteMarigoldBorderActive} strokeDasharray="3 3" />
                                    <title>{s("Today")}</title>
                                </g>
                            )}
                            {links.map(arrow)}
                            {rows.map(bar)}
                        </svg>
                    </div>
                </div>
            )}
        </FluentProvider>
    );
}
