import { IInputs, IOutputs } from "./generated/ManifestTypes";
import * as React from "react";
import { cellRendererOverrides } from "./customizers/CellRendererOverrides";
import { PAOneGridCustomizer } from "./types";

export class ProgressBar implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    public init(context: ComponentFramework.Context<IInputs>): void {
        // The Power Apps grid passes an event name: answer it with the cell renderers
        const eventName = context.parameters.EventName.raw;
        if (eventName) {
            const customizer: PAOneGridCustomizer = { cellRendererOverrides };
            // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
            (context as any).factory.fireEvent(eventName, customizer);
        }
    }

    public updateView(): React.ReactElement {
        return React.createElement(React.Fragment);
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        // nothing to release
    }
}
