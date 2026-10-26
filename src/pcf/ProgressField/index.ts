import { IInputs, IOutputs } from "./generated/ManifestTypes";
import * as React from "react";
import { FluentProvider, Theme, webLightTheme } from "@fluentui/react-components";
import { ProgressCell } from "../shared/ProgressCell";
import { progressPercent } from "../shared/progress";

export class ProgressField implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    public init(): void {
        // read-only: nothing to set up
    }

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        const theme = (context as unknown as { fluentDesignLanguage?: { tokenTheme?: Theme } }).fluentDesignLanguage?.tokenTheme ?? webLightTheme;
        const pct = progressPercent(context.parameters.value.raw) ?? 0;
        return React.createElement(FluentProvider, { theme, style: { background: "transparent" } }, React.createElement(ProgressCell, { pct }));
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        // nothing to release
    }
}
