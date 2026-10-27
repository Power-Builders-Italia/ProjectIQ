import * as React from "react";
import { makeStyles, ProgressBar } from "@fluentui/react-components";
import { progressLabel } from "./progress";

// Brand green bar on a light grey track, percentage on the right (approved mockup A, single colour)
const useStyles = makeStyles({
    cell: { display: "flex", alignItems: "center", columnGap: "10px", width: "100%", minWidth: "120px", boxSizing: "border-box" },
    track: { flexGrow: 1, minWidth: "40px", height: "8px", backgroundColor: "#e8e6e5", borderRadius: "4px" },
    bar: { backgroundColor: "#0c723d", borderRadius: "4px" },
    label: { minWidth: "40px", textAlign: "right", fontVariantNumeric: "tabular-nums" },
});

export interface ProgressCellProps {
    /** Percent, 0-100. */
    pct: number;
    /** Replaces the default label (e.g. an editable value). */
    label?: React.ReactNode;
}

export function ProgressCell({ pct, label }: ProgressCellProps): React.ReactElement {
    const s = useStyles();
    const text = progressLabel(pct);
    return (
        <div className={s.cell} title={text}>
            <ProgressBar className={s.track} bar={{ className: s.bar }} value={pct / 100} thickness="large" shape="rounded" aria-label={text} />
            <span className={s.label}>{label ?? text}</span>
        </div>
    );
}
