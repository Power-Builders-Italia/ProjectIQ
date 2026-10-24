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
export const ChevronLeftIcon = icon("M10.35 3.15a.5.5 0 0 1 0 .7L6.21 8l4.14 4.15a.5.5 0 0 1-.7.7l-4.5-4.5a.5.5 0 0 1 0-.7l4.5-4.5a.5.5 0 0 1 .7 0Z");
export const CheckmarkIcon = icon("M13.86 3.66a.5.5 0 0 1-.02.7l-7.93 7.48a.6.6 0 0 1-.84-.02L2.15 8.9a.5.5 0 0 1 .7-.7l2.65 2.62 7.65-7.2a.5.5 0 0 1 .7.03Z");
export const DismissIcon = icon("M2.59 2.72 2.65 2.65a.5.5 0 0 1 .64-.06l.07.06L8 7.29l4.65-4.64a.5.5 0 0 1 .7.7L8.71 8l4.64 4.65a.5.5 0 0 1-.7.7L8 8.71l-4.65 4.64a.5.5 0 0 1-.7-.7L7.29 8 2.65 3.35a.5.5 0 0 1-.06-.63Z");
export const SendIcon = icon("M1.72 1.05a.5.5 0 0 1 .53-.06l12.5 6.5a.5.5 0 0 1 0 .89l-12.5 6.5a.5.5 0 0 1-.7-.58L3.1 8 1.55 1.7a.5.5 0 0 1 .17-.65ZM4 8.5l-1.2 4.62L13.4 8 2.8 2.88 4 7.5h5.5a.5.5 0 0 1 0 1H4Z");
