import { IInputs, IOutputs } from "./generated/ManifestTypes";
import * as React from "react";
import { ResourceLoadApp } from "./ResourceLoadApp";

export class ResourceLoad implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    private refreshKey = 0;

    public init(context: ComponentFramework.Context<IInputs>): void {
        context.mode.trackContainerResize(true);
    }

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        // a subgrid refresh reloads the data
        const dataset = context.parameters.resources;
        if (context.updatedProperties.includes("dataset") || context.updatedProperties.includes("resources")) {
            if (!dataset.loading) this.refreshKey++;
        }
        return React.createElement(ResourceLoadApp, { context, refreshKey: this.refreshKey });
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        // nothing to release
    }
}
