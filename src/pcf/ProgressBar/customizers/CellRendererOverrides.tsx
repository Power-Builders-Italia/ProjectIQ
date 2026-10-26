import * as React from "react";
import { CellRendererOverrides, CellRendererProps, ColumnDataType, GetRendererParams } from "../types";
import { isProgressColumn, progressPercent } from "../../shared/progress";
import { ProgressCell } from "../../shared/ProgressCell";

const logged = new Set<string>();
const seen = new Set<string>();

const renderProgress = (props: CellRendererProps, params: GetRendererParams) => {
    const col = params.colDefs[params.columnIndex];
    const key = `${col?.name}:${col?.dataType}`;
    if (!seen.has(key)) {
        seen.add(key);
        const t = (window as unknown as Record<string, { columns: string[] } | undefined>).OP365ProgressBar;
        t?.columns.push(key);
    }
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
