import * as React from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { createDOMRenderer, FluentProvider, RendererProvider, webDarkTheme, webLightTheme } from '@fluentui/react-components';
import { BaseCopilotComponent, createCopilotTextContent } from '@microsoft/sp-copilot-component';

import { AgentApp } from '../ui/AgentApp';
import { AgentContext, type IAgentContext } from '../ui/AgentContext';
import { localToday } from '../ui/format';
import { createService, loadSettings } from '../services/spfx';
import { setCulture } from '../i18n';
import type { IntentKey } from '../intents';
import type { ProjectIQService } from '../services/ProjectIQService';
import type { AgentSettings } from '../settings';

/** Copilot keeps at most 10 KB of component context; larger context blocks the message. */
const MAX_CONTEXT = 9000;

/** Shared by every ProjectIQ Copilot Component: theme, display mode, Dataverse service and the view of the tool. */
export default abstract class ProjectIQCopilotComponentBase<TProperties extends object> extends BaseCopilotComponent<TProperties> {
  protected abstract intentKey: IntentKey;
  private _root?: Root;
  private _ready?: Promise<{ service: ProjectIQService; settings: AgentSettings }>;
  private _renderer?: ReturnType<typeof createDOMRenderer>;
  private _observer?: ResizeObserver;
  private _size = '';

  protected render(): void {
    // Texts and formats follow the SharePoint UI language of the user (English when it is not translated).
    setCulture(this.context.pageContext?.cultureInfo?.currentUICultureName);
    if (!this._ready) {
      this._ready = loadSettings(this.context).then(async settings => ({ settings, service: await createService(this.context, settings) }));
      this._ready.catch(() => { this._ready = undefined; });
    }
    const host = this.hostContext;
    const fullscreen = host.displayMode === 'fullscreen';
    const canExpand = !fullscreen && (host.availableDisplayModes || []).indexOf('fullscreen') >= 0;
    const width = host.containerDimensions?.width || host.containerDimensions?.maxWidth || 0;
    const targetDocument = this.context.domElement.ownerDocument;
    if (!this._renderer) this._renderer = createDOMRenderer(targetDocument);
    if (!this._root) this._root = createRoot(this.context.domElement);

    const agent: IAgentContext = {
      ready: this._ready,
      today: localToday(),
      fullscreen,
      wide: fullscreen || width >= 720,
      onRequestFullscreen: canExpand ? this._expand : undefined,
      openLink: this._openLink,
      followUp: this._followUp,
      setModelContext: this._setModelContext,
    };
    this._root.render(
      <RendererProvider renderer={this._renderer} targetDocument={targetDocument}>
        <FluentProvider theme={host.theme === 'dark' ? webDarkTheme : webLightTheme} targetDocument={targetDocument} style={{ background: 'transparent' }}>
          <AgentContext.Provider value={agent}>
            <div ref={this._measure}>
              <AgentApp intent={this.intentKey} properties={this.properties as Record<string, unknown>} />
            </div>
          </AgentContext.Provider>
        </FluentProvider>
      </RendererProvider>
    );
  }

  protected onHostContextChanged(): void {
    this.render();
  }

  protected onTeardown(reason: string | undefined): Promise<void> {
    this._observer?.disconnect();
    this._observer = undefined;
    this._root?.unmount();
    this._root = undefined;
    return super.onTeardown(reason);
  }

  /**
   * The host sizes the frame on the first paint (the loading spinner) and does not always follow the content
   * when the data arrives: the card was cut below the KPIs. Report the real size of the content on every change.
   */
  private _measure = (element: HTMLDivElement | null): void => {
    this._observer?.disconnect();
    this._observer = undefined;
    if (!element || typeof ResizeObserver === 'undefined') return;
    this._observer = new ResizeObserver(() => {
      const width = Math.ceil(element.getBoundingClientRect().width);
      const height = Math.ceil(element.getBoundingClientRect().height);
      const size = `${width}x${height}`;
      if (!height || size === this._size) return;
      this._size = size;
      this.requestSizeChangeAsync(width, height).catch(() => undefined);
    });
    this._observer.observe(element);
  };

  private _expand = (): void => {
    this.requestDisplayModeAsync('fullscreen').catch(() => undefined);
  };

  private _openLink = (url: string): void => {
    this.context.copilotBridge.openLinkAsync(url).then(r => {
      if (r?.isError) window.open(url, '_blank', 'noopener');
    }).catch(() => window.open(url, '_blank', 'noopener'));
  };

  private _followUp = (prompt: string): void => {
    this.context.copilotBridge.sendFollowUpMessageAsync([createCopilotTextContent(prompt)]).catch(() => undefined);
  };

  private _setModelContext = (text: string): void => {
    const content = text.length > MAX_CONTEXT ? text.substring(0, MAX_CONTEXT) + '…' : text;
    this.context.copilotBridge.updateModelContextAsync({ content: [createCopilotTextContent(content)] }).catch(() => undefined);
  };
}
