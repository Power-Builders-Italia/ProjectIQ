import * as React from "react";
import { makeStyles, ProgressBar } from "@fluentui/react-components";
import { CellRendererOverrides, CellRendererProps, GetRendererParams } from "../types";
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

const renderProgress = (props: CellRendererProps, params: GetRendererParams) => {
    if (!isProgressColumn(params.colDefs[params.columnIndex]?.name)) return undefined; // default renderer
    const pct = progressPercent(props.value);
    return pct === null ? undefined : <ProgressCell pct={pct} />;
};

export const cellRendererOverrides: CellRendererOverrides = {
    Decimal: renderProgress,
    FloatingPoint: renderProgress,
};
