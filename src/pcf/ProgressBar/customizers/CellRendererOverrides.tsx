import * as React from "react";
import { makeStyles, ProgressBar } from "@fluentui/react-components";
import { CellRendererOverrides, CellRendererProps, ColumnDataType, GetRendererParams } from "../types";
import { isProgressColumn, progressLabel, progressPercent } from "../../shared/progress";

// Brand green bar on a light grey track (mockup A, single colour)
const useStyles = makeStyles({
    cell: { display: "flex", alignItems: "center", columnGap: "10px", width: "100%", height: "100%", boxSizing: "border-box" },
    track: { flexGrow: 1, minWidth: "40px", height: "8px", backgroundColor: "#e8e6e5", borderRadius: "4px" },
    bar: { backgroundColor: "#0c723d", borderRadius: "4px" },
    label: { minWidth: "40px", textAlign: "right", fontVariantNumeric: "tabular-nums" },
});

const ProgressCell: React.FC<{ pct: number }> = ({ pct }) => {
    const s = useStyles();
    const label = progressLabel(pct);
    return (
        <div className={s.cell} title={label}>
            <ProgressBar className={s.track} bar={{ className: s.bar }} value={pct / 100} thickness="large" shape="rounded" aria-label={label} />
            <span className={s.label}>{label}</span>
        </div>
    );
};

const logged = new Set<string>();

const renderProgress = (props: CellRendererProps, params: GetRendererParams) => {
    const col = params.colDefs[params.columnIndex];
    if (!isProgressColumn(col?.name) && !isProgressColumn(col?.colId)) return undefined; // default renderer
    const pct = progressPercent(props.value, props.formattedValue);
    if (!logged.has(col.name)) {
        logged.add(col.name);
        console.info("[OP365.ProgressBar] column", col.name, col.dataType, typeof props.value, pct);
    }
    return pct === null ? undefined : <ProgressCell pct={pct} />;
};

// Decimal is the type of Progress %; the other numeric types cover a column whose type the grid reports differently
const NUMERIC: ColumnDataType[] = ["Decimal", "FloatingPoint", "Integer", "Currency"];
export const cellRendererOverrides: CellRendererOverrides = Object.fromEntries(NUMERIC.map(t => [t, renderProgress]));
