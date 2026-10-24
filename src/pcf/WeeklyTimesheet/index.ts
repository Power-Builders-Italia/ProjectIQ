import { IInputs, IOutputs } from "./generated/ManifestTypes";
import * as React from "react";
import { WeeklyTimesheetApp } from "./WeeklyTimesheetApp";

export class WeeklyTimesheet implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    private refreshKey = 0;

    public init(context: ComponentFramework.Context<IInputs>): void {
        context.mode.trackContainerResize(true);
    }

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        // a subgrid refresh reloads the data
        const dataset = context.parameters.entries;
        if (context.updatedProperties.includes("dataset") || context.updatedProperties.includes("entries")) {
            if (!dataset.loading) this.refreshKey++;
        }
        return React.createElement(WeeklyTimesheetApp, { context, refreshKey: this.refreshKey });
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        // nothing to release
    }
}
