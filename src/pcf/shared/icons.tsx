import * as React from "react";

// Minimal 16px icons drawn from the Fluent System Icons outlines (bundling @fluentui/react-icons
// needs React 17's jsx-runtime, while the platform library is React 16.14).

const icon = (d: string) => function Icon(): React.ReactElement {
    return (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d={d} />
        </svg>
    );
};

export const AddIcon = icon("M8 2.5a.5.5 0 0 0-1 0V7H2.5a.5.5 0 0 0 0 1H7v4.5a.5.5 0 0 0 1 0V8h4.5a.5.5 0 0 0 0-1H8V2.5Z");
export const RefreshIcon = icon("M3 8a5 5 0 0 1 9-3h-2a.5.5 0 0 0 0 1h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-1 0v1.7A6 6 0 1 0 14 8a.5.5 0 0 0-1 0A5 5 0 0 1 3 8Z");
export const ChevronRightIcon = icon("M5.65 3.15a.5.5 0 0 1 .7 0l4.5 4.5a.5.5 0 0 1 0 .7l-4.5 4.5a.5.5 0 0 1-.7-.7L9.79 8 5.65 3.85a.5.5 0 0 1 0-.7Z");
export const ChevronDownIcon = icon("M3.15 5.65a.5.5 0 0 1 .7 0L8 9.79l4.15-4.14a.5.5 0 0 1 .7.7l-4.5 4.5a.5.5 0 0 1-.7 0l-4.5-4.5a.5.5 0 0 1 0-.7Z");
export const ExpandIcon = icon("M4.15 3.15a.5.5 0 0 1 .7 0L8 6.29l3.15-3.14a.5.5 0 0 1 .7.7l-3.5 3.5a.5.5 0 0 1-.7 0l-3.5-3.5a.5.5 0 0 1 0-.7Zm0 5a.5.5 0 0 1 .7 0L8 11.29l3.15-3.14a.5.5 0 0 1 .7.7l-3.5 3.5a.5.5 0 0 1-.7 0l-3.5-3.5a.5.5 0 0 1 0-.7Z");
export const CollapseIcon = icon("M7.65 3.15a.5.5 0 0 1 .7 0l3.5 3.5a.5.5 0 0 1-.7.7L8 4.21 4.85 7.35a.5.5 0 1 1-.7-.7l3.5-3.5Zm0 5a.5.5 0 0 1 .7 0l3.5 3.5a.5.5 0 0 1-.7.7L8 9.21l-3.15 3.14a.5.5 0 0 1-.7-.7l3.5-3.5Z");
