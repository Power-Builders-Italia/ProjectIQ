import { IInputs, IOutputs } from "./generated/ManifestTypes";
import * as React from "react";
import { CostSummaryApp } from "./CostSummaryApp";

export class CostSummary implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    private refreshKey = 0;
    private last: number | null = null;

    public init(context: ComponentFramework.Context<IInputs>): void {
        context.mode.trackContainerResize(true);
    }

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        // Actual Cost changes after a save (plugins recalculate it): reload the summary
        const value = context.parameters.value.raw;
        if (value !== this.last) { this.last = value; this.refreshKey++; }
        return React.createElement(CostSummaryApp, { context, refreshKey: this.refreshKey });
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        // nothing to release
    }
}
