import { IInputs, IOutputs } from "./generated/ManifestTypes";
import * as React from "react";
import { WbsTreeGridApp } from "./WbsTreeGridApp";

export class WbsTreeGrid implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    private refreshKey = 0;

    public init(context: ComponentFramework.Context<IInputs>): void {
        context.mode.trackContainerResize(true);
    }

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        // a dataset refresh (subgrid refresh, record saved) reloads the tree
        const dataset = context.parameters.nodes;
        if (context.updatedProperties.includes("dataset") || context.updatedProperties.includes("nodes")) {
            if (!dataset.loading) this.refreshKey++;
        }
        return React.createElement(WbsTreeGridApp, { context, refreshKey: this.refreshKey });
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        // nothing to release
    }
}
