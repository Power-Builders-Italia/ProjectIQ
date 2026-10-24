import { IInputs, IOutputs } from "./generated/ManifestTypes";
import * as React from "react";
import { QuoteComparisonApp } from "./QuoteComparisonApp";

export class QuoteComparison implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    private refreshKey = 0;
    private last: number | null = null;

    public init(context: ComponentFramework.Context<IInputs>): void {
        context.mode.trackContainerResize(true);
    }

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        // Responses changes when suppliers quote: reload the comparison
        const value = context.parameters.value.raw;
        if (value !== this.last) { this.last = value; this.refreshKey++; }
        return React.createElement(QuoteComparisonApp, { context, refreshKey: this.refreshKey });
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        // nothing to release
    }
}
