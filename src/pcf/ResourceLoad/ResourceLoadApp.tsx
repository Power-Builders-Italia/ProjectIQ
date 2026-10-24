import * as React from "react";
import {
    Dropdown, FluentProvider, MessageBar, MessageBarBody, Option, Spinner, Toolbar, ToolbarButton, ToolbarDivider, Tooltip,
    makeStyles, tokens, webLightTheme, Theme,
} from "@fluentui/react-components";
import { IInputs } from "./generated/ManifestTypes";
import { fromDay, toDay } from "../shared/dates";
import { weekStart } from "../shared/timesheet";
import { level, LoadLevel, resourceLoad, ResourceLoadRow, WeekLoad } from "../shared/load";
import { loadLoadData } from "../shared/execution";
import { ChevronLeftIcon, ChevronRightIcon, RefreshIcon } from "../shared/icons";

const useStyles = makeStyles({
    root: { display: "flex", flexDirection: "column", gap: tokens.spacingVerticalS, width: "100%" },
    toolbarRight: { marginLeft: "auto", display: "flex", alignItems: "center", gap: tokens.spacingHorizontalS },
    scroll: { overflowX: "auto" },
    grid: { borderCollapse: "collapse", fontSize: tokens.fontSizeBase200, width: "100%" },
    th: {
        padding: `${tokens.spacingVerticalXS} ${tokens.spacingHorizontalS}`, textAlign: "center", whiteSpace: "nowrap",
        fontWeight: tokens.fontWeightSemibold, borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    },
    name: { textAlign: "left", minWidth: "180px", padding: `${tokens.spacingVerticalXS} ${tokens.spacingHorizontalS}`, whiteSpace: "nowrap" },
    sub: { color: tokens.colorNeutralForeground3 },
    cell: { padding: "2px", minWidth: "64px" },
    box: { borderRadius: tokens.borderRadiusMedium, padding: `${tokens.spacingVerticalXS} 0`, textAlign: "center" },
    free: { backgroundColor: tokens.colorNeutralBackground3, color: tokens.colorNeutralForeground3 },
    ok: { backgroundColor: tokens.colorPaletteGreenBackground2, color: tokens.colorPaletteGreenForeground2 },
    full: { backgroundColor: tokens.colorPaletteYellowBackground2, color: tokens.colorPaletteMarigoldForeground2 },
    over: { backgroundColor: tokens.colorPaletteRedBackground2, color: tokens.colorPaletteRedForeground2, fontWeight: tokens.fontWeightSemibold },
    legend: { display: "flex", gap: tokens.spacingHorizontalS, alignItems: "center", fontSize: tokens.fontSizeBase200 },
    swatch: { display: "inline-block", width: "28px" },
});

interface Props {
    context: ComponentFramework.Context<IInputs>;
    refreshKey: number;
}

export function ResourceLoadApp({ context, refreshKey }: Props): React.ReactElement {
    const styles = useStyles();
    const s = (key: string): string => context.resources.getString(key);
    const theme = (context as unknown as { fluentDesignLanguage?: { tokenTheme?: Theme } }).fluentDesignLanguage?.tokenTheme ?? webLightTheme;
    const today = toDay(new Date())!;

    const [first, setFirst] = React.useState(weekStart(today));
    const [weeks, setWeeks] = React.useState(8);
    const [rows, setRows] = React.useState<ResourceLoadRow[]>([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string>();
    const [reload, setReload] = React.useState(0);

    React.useEffect(() => {
        let cancelled = false;
        const load = async (): Promise<void> => {
            setLoading(true);
            try {
                const data = await loadLoadData(context.webAPI, first, first + weeks * 7 - 1);
                if (cancelled) return;
                setRows(resourceLoad(data.resources, data.allocations, data.absences, first, weeks));
                setError(undefined);
            } catch (e) {
                if (!cancelled) setError(`${s("Error_Load")}: ${(e as Error).message}`);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        void load();
        return () => { cancelled = true; };
    }, [first, weeks, refreshKey, reload]);

    const day = (d: number, opts: Intl.DateTimeFormatOptions): string => fromDay(d).toLocaleDateString(undefined, { timeZone: "UTC", ...opts });
    const h = (v: number): string => String(Math.round(v));
    const levelClass: Record<LoadLevel, string> = { free: styles.free, ok: styles.ok, full: styles.full, over: styles.over };
    const tip = (w: WeekLoad): string => {
        const lines = [...w.projects.entries()].sort((a, b) => b[1] - a[1]).map(([p, v]) => `${p}: ${h(v)} h`);
        return [`${s("Allocated")} ${h(w.load)} h / ${s("Capacity")} ${h(w.capacity)} h`, ...lines].join("\n");
    };

    return (
        <FluentProvider theme={theme}>
            <div className={styles.root}>
                <Toolbar size="small">
                    <ToolbarButton icon={<ChevronLeftIcon />} aria-label={s("Previous")} onClick={() => setFirst(f => f - 7 * weeks)} />
                    <ToolbarButton onClick={() => setFirst(weekStart(today))}>{s("This_Week")}</ToolbarButton>
                    <ToolbarButton icon={<ChevronRightIcon />} aria-label={s("Next")} onClick={() => setFirst(f => f + 7 * weeks)} />
                    <ToolbarDivider />
                    <Dropdown size="small" value={s("Weeks").replace("{0}", String(weeks))} selectedOptions={[String(weeks)]}
                        onOptionSelect={(_, d) => setWeeks(Number(d.optionValue))}>
                        {[4, 8, 12, 26].map(n => <Option key={n} value={String(n)}>{s("Weeks").replace("{0}", String(n))}</Option>)}
                    </Dropdown>
                    <ToolbarButton icon={<RefreshIcon />} onClick={() => setReload(r => r + 1)}>{s("Refresh")}</ToolbarButton>
                    <div className={styles.toolbarRight}>
                        {loading && <Spinner size="tiny" />}
                        <div className={styles.legend}>
                            {(["free", "ok", "full", "over"] as LoadLevel[]).map(l => (
                                <span key={l}><span className={`${styles.box} ${styles.swatch} ${levelClass[l]}`}>&nbsp;</span> {s("Level_" + l)}</span>
                            ))}
                        </div>
                    </div>
                </Toolbar>
                {error && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>}
                <div className={styles.scroll}>
                    <table className={styles.grid} aria-label={s("Control_Name")}>
                        <thead>
                            <tr>
                                <th className={`${styles.th} ${styles.name}`}>{s("Column_Resource")}</th>
                                {Array.from({ length: weeks }, (_, i) => (
                                    <th key={i} className={styles.th}>{day(first + i * 7, { day: "numeric", month: "short" })}</th>
                                ))}
                                <th className={styles.th}><Tooltip content={s("Unscheduled_Tip")} relationship="description"><span>{s("Unscheduled")}</span></Tooltip></th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map(r => (
                                <tr key={r.resource.id}>
                                    <td className={styles.name}>{r.resource.name} <span className={styles.sub}>{h(r.resource.weeklyHours)} h</span></td>
                                    {r.weeks.map((w, i) => (
                                        <td key={i} className={styles.cell}>
                                            <Tooltip content={tip(w)} relationship="description">
                                                <div className={`${styles.box} ${levelClass[level(w)]}`} tabIndex={0}>
                                                    {w.capacity > 0 ? `${Math.round((w.load / w.capacity) * 100)}%` : w.load > 0 ? `${h(w.load)} h` : "–"}
                                                </div>
                                            </Tooltip>
                                        </td>
                                    ))}
                                    <td className={styles.cell}><div className={styles.box}>{r.unscheduled ? `${h(r.unscheduled)} h` : ""}</div></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </FluentProvider>
    );
}
