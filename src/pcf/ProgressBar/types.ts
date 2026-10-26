import * as React from "react";

// Subset of the Power Apps grid customizer contract (PowerApps-Samples/PowerAppsGridCustomizerControl/types.ts).

export interface CellRendererProps {
    readonly value: unknown;
    readonly formattedValue?: string;
    readonly rowHeight?: number;
}

export interface ColumnDefinition {
    readonly name: string;
    readonly colId?: string;
    readonly dataType: string;
}

export interface GetRendererParams {
    readonly colDefs: ColumnDefinition[];
    readonly columnIndex: number;
}

export type ColumnDataType = "Decimal" | "FloatingPoint" | "Integer" | "Currency";

export type CellRendererOverrides = Partial<Record<ColumnDataType,
    (props: CellRendererProps, params: GetRendererParams) => React.ReactElement | null | undefined>>;

export interface PAOneGridCustomizer {
    cellRendererOverrides?: CellRendererOverrides;
}
