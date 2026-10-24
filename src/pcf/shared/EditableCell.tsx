import * as React from "react";
import { Input, makeStyles, tokens } from "@fluentui/react-components";

const useStyles = makeStyles({
    value: {
        cursor: "text",
        minHeight: "20px",
        display: "block",
        borderRadius: tokens.borderRadiusSmall,
        ":hover": { outline: `1px solid ${tokens.colorNeutralStroke1}` },
    },
    input: { width: "100%", minWidth: "80px" },
});

export interface EditableCellProps {
    /** Text shown when not editing. */
    display: string;
    /** Raw value put in the editor ("" when empty). */
    value: string;
    type: "number" | "date";
    min?: number;
    max?: number;
    disabled?: boolean;
    ariaLabel: string;
    onCommit: (value: string) => void;
}

/** Shows a value; click or Enter opens a Fluent Input, Enter or blur saves, Escape cancels. */
export function EditableCell(props: EditableCellProps): React.ReactElement {
    const styles = useStyles();
    const [editing, setEditing] = React.useState(false);
    const [draft, setDraft] = React.useState(props.value);

    if (props.disabled) return <span>{props.display}</span>;
    if (!editing) {
        return (
            <span className={styles.value} role="button" tabIndex={0} aria-label={props.ariaLabel}
                onClick={() => { setDraft(props.value); setEditing(true); }}
                onKeyDown={e => { if (e.key === "Enter") { setDraft(props.value); setEditing(true); } }}>
                {props.display || " "}
            </span>
        );
    }
    const commit = (): void => {
        setEditing(false);
        if (draft !== props.value) props.onCommit(draft);
    };
    return (
        <Input className={styles.input} size="small" type={props.type} value={draft} min={props.min} max={props.max}
            aria-label={props.ariaLabel} autoFocus
            onChange={(_, d) => setDraft(d.value)} onBlur={commit}
            onKeyDown={e => {
                if (e.key === "Enter") commit();
                if (e.key === "Escape") setEditing(false);
            }} />
    );
}
