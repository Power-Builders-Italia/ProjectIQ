import * as React from "react";
import {
    FluentProvider, MessageBar, MessageBarBody, ProgressBar, Spinner, Table, TableBody, TableCell, TableHeader,
    TableHeaderCell, TableRow, makeStyles, tokens, webLightTheme, Theme,
} from "@fluentui/react-components";
import { IInputs } from "./generated/ManifestTypes";
import { buildTree } from "../shared/wbs";
import { currencySymbol, hostRecordId, loadNodes } from "../shared/data";
import { loadProjectCosts } from "../shared/execution";
import { costSummary, CostSummary as Summary } from "../shared/cost";

const useStyles = makeStyles({
    root: { display: "flex", flexDirection: "column", gap: tokens.spacingVerticalM, width: "100%" },
    kpis: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: tokens.spacingHorizontalM },
    kpi: {
        border: `1px solid ${tokens.colorNeutralStroke2}`, borderRadius: tokens.borderRadiusMedium,
        padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`, backgroundColor: tokens.colorNeutralBackground1,
    },
    kpiLabel: { color: tokens.colorNeutralForeground3, fontSize: tokens.fontSizeBase200 },
    kpiValue: { fontSize: tokens.fontSizeBase500, fontWeight: tokens.fontWeightSemibold },
    kpiSub: { color: tokens.colorNeutralForeground3, fontSize: tokens.fontSizeBase200 },
    bad: { color: tokens.colorPaletteRedForeground1 },
    good: { color: tokens.colorPaletteGreenForeground1 },
    num: { textAlign: "right" },
    bar: { minWidth: "120px" },
});

interface Props {
    context: ComponentFramework.Context<IInputs>;
    refreshKey: number;
}

export function CostSummaryApp({ context, refreshKey }: Props): React.ReactElement {
    const styles = useStyles();
    const s = (key: string): string => context.resources.getString(key);
    const theme = (context as unknown as { fluentDesignLanguage?: { tokenTheme?: Theme } }).fluentDesignLanguage?.tokenTheme ?? webLightTheme;
    const projectId = hostRecordId(context as ComponentFramework.Context<unknown>);

    const [summary, setSummary] = React.useState<Summary>();
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string>();
    const [symbol, setSymbol] = React.useState<string>();

    React.useEffect(() => {
        if (!projectId) { setLoading(false); return; }
        let cancelled = false;
        const load = async (): Promise<void> => {
            setLoading(true);
            try {
                const [items, costs, sym] = await Promise.all([loadNodes(context.webAPI, projectId), loadProjectCosts(context.webAPI, projectId),
                    currencySymbol(context.webAPI, "op365_project", projectId)]);
                if (cancelled) return;
                setSymbol(sym);
                const nodeCost = [...costs.nodeActuals.values()].reduce((t, a) => t + a.actualCost, 0);
                const nodeHours = [...costs.nodeActuals.values()].reduce((t, a) => t + a.actualHours, 0);
                setSummary(costSummary(buildTree(items), costs.nodeActuals, {
                    contract: costs.contract, labour: costs.labour, materials: costs.materials, progressPct: costs.progressPct,
                    unassignedCost: Math.max(0, costs.actualCost - nodeCost), unassignedHours: Math.max(0, costs.actualHours - nodeHours),
                }));
                setError(undefined);
            } catch (e) {
                if (!cancelled) setError(`${s("Error_Load")}: ${(e as Error).message}`);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        void load();
        return () => { cancelled = true; };
    }, [projectId, refreshKey]);

    if (!projectId) {
        return <FluentProvider theme={theme}><MessageBar><MessageBarBody>{s("Save_Project")}</MessageBarBody></MessageBar></FluentProvider>;
    }
    // amounts in the project currency (#33)
    const money = (v: number): string => context.formatting.formatCurrency(v, 0, symbol);
    const hours = (v: number): string => context.formatting.formatDecimal(v, 1);
    const pct = (v: number): string => `${Math.round(v * 100)}%`;

    const kpi = (label: string, value: string, sub?: string, cls?: string): React.ReactElement => (
        <div className={styles.kpi}>
            <div className={styles.kpiLabel}>{label}</div>
            <div className={`${styles.kpiValue} ${cls ?? ""}`}>{value}</div>
            {sub && <div className={styles.kpiSub}>{sub}</div>}
        </div>
    );

    return (
        <FluentProvider theme={theme}>
            <div className={styles.root}>
                {error && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>}
                {loading && !summary && <Spinner size="small" />}
                {summary && (
                    <>
                        <div className={styles.kpis}>
                            {kpi(s("Kpi_Contract"), money(summary.contract))}
                            {kpi(s("Kpi_Budget"), money(summary.budget))}
                            {kpi(s("Kpi_Actual"), money(summary.actual),
                                `${s("Labour")} ${money(summary.labour)} · ${s("Materials")} ${money(summary.materials)}`,
                                summary.actual > summary.budget && summary.budget > 0 ? styles.bad : undefined)}
                            {kpi(s("Kpi_Eac"), money(summary.eac), s("Kpi_Eac_Tip"), summary.eac > summary.budget && summary.budget > 0 ? styles.bad : undefined)}
                            {kpi(s("Kpi_Margin"), money(summary.margin),
                                summary.contract > 0 ? pct(summary.margin / summary.contract) : undefined, summary.margin < 0 ? styles.bad : styles.good)}
                        </div>
                        {summary.lines.length > 0 && (
                            <Table size="small" aria-label={s("Control_Name")}>
                                <TableHeader>
                                    <TableRow>
                                        <TableHeaderCell>{s("Column_Branch")}</TableHeaderCell>
                                        <TableHeaderCell className={styles.num}>{s("Column_Budget")}</TableHeaderCell>
                                        <TableHeaderCell className={styles.num}>{s("Column_Actual")}</TableHeaderCell>
                                        <TableHeaderCell className={styles.num}>{s("Column_Variance")}</TableHeaderCell>
                                        <TableHeaderCell>{s("Column_Spent")}</TableHeaderCell>
                                        <TableHeaderCell className={styles.num}>{s("Column_Hours")}</TableHeaderCell>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {summary.lines.map(l => (
                                        <TableRow key={l.id || "unassigned"}>
                                            <TableCell>{l.id ? `${l.code} ${l.name}`.trim() : s("Unassigned")}</TableCell>
                                            <TableCell className={styles.num}>{money(l.budget)}</TableCell>
                                            <TableCell className={styles.num}>{money(l.actual)}</TableCell>
                                            <TableCell className={`${styles.num} ${l.variance > 0 ? styles.bad : ""}`}>{money(l.variance)}</TableCell>
                                            <TableCell className={styles.bar}>
                                                {l.budget > 0 && (
                                                    <ProgressBar value={Math.min(1, l.spent)} thickness="large"
                                                        color={l.spent > 1 ? "error" : l.spent >= 0.9 ? "warning" : "brand"}
                                                        aria-label={pct(l.spent)} title={pct(l.spent)} />
                                                )}
                                            </TableCell>
                                            <TableCell className={styles.num}>{hours(l.actualHours)} / {hours(l.budgetHours)}</TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        )}
                    </>
                )}
            </div>
        </FluentProvider>
    );
}
