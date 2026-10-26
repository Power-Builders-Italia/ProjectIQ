import { IInputs, IOutputs } from "./generated/ManifestTypes";
import * as React from "react";
import { cellRendererOverrides } from "./customizers/CellRendererOverrides";
import { PAOneGridCustomizer } from "./types";

// Trace for support: window.OP365ProgressBar shows whether the grid loaded the customizer and which columns it saw
const trace: { loaded: string; init?: string | null; columns: string[] } = { loaded: new Date().toISOString(), columns: [] };
(window as unknown as Record<string, unknown>).OP365ProgressBar = trace;

export class ProgressBar implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    public init(context: ComponentFramework.Context<IInputs>): void {
        // The Power Apps grid passes an event name: answer it with the cell renderers
        const eventName = context.parameters.EventName.raw;
        trace.init = eventName;
        console.info("[OP365.ProgressBar] init", eventName);
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
