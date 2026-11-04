// Opens records from the PCF controls in the model-driven side dialog (form on the right, control still visible).

interface XrmNavigation {
    navigateTo(pageInput: Record<string, unknown>, navigationOptions: Record<string, unknown>): Promise<unknown>;
}

const xrmNavigation = (): XrmNavigation | undefined =>
    (window as unknown as { Xrm?: { Navigation?: XrmNavigation } }).Xrm?.Navigation;

/**
 * Opens the main form of a record in a side dialog that takes half of the window.
 * The promise resolves when the user closes the dialog. Without Xrm (e.g. test harness)
 * it falls back to the full-page form of the PCF navigation API.
 */
export async function openRecordInSidePane(
    navigation: ComponentFramework.Navigation, entityName: string, entityId: string,
): Promise<void> {
    const xrm = xrmNavigation();
    if (!xrm) {
        await navigation.openForm({ entityName, entityId });
        return;
    }
    try {
        await xrm.navigateTo(
            { pageType: "entityrecord", entityName, entityId },
            { target: 2, position: 2, width: { value: 50, unit: "%" } },
        );
    } catch {
        await navigation.openForm({ entityName, entityId });
    }
}
