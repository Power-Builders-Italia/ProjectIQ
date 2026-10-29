// Building blocks shared by the views: card shell, KPI tiles, health badge, budget meter, loading and error states.
import * as React from 'react';
import {
  Badge, Button, makeStyles, mergeClasses, MessageBar, MessageBarBody, MessageBarTitle, Spinner, Text, tokens, Tooltip,
} from '@fluentui/react-components';
import { ArrowClockwise20Regular, ArrowMaximize20Regular, Open16Regular } from '@fluentui/react-icons';

import { useAgent } from './AgentContext';
import type { HealthLevel } from '../logic/portfolio';
import { SettingsMissingError } from '../services/spfx';
import { DataverseError } from '../services/DataverseClient';
import { ENVIRONMENT_URL_KEY } from '../settings';
import { strings } from '../i18n';

const useStyles = makeStyles({
  card: {
    width: '100%', minWidth: 0, boxSizing: 'border-box', overflow: 'hidden', borderRadius: tokens.borderRadiusXLarge,
    border: `1px solid ${tokens.colorNeutralStroke2}`, backgroundColor: tokens.colorNeutralBackground1, boxShadow: tokens.shadow4,
    fontFamily: tokens.fontFamilyBase, color: tokens.colorNeutralForeground1,
  },
  accent: { height: '5px', backgroundImage: `linear-gradient(90deg, ${tokens.colorBrandBackground} 0%, ${tokens.colorPaletteTealBackground2} 60%, ${tokens.colorPaletteGreenBackground3} 100%)` },
  body: { display: 'flex', flexDirection: 'column', gap: tokens.spacingVerticalM, padding: '16px' },
  header: { display: 'flex', alignItems: 'flex-start', gap: tokens.spacingHorizontalM },
  heading: { display: 'flex', flexDirection: 'column', gap: '2px', minWidth: 0, flexGrow: 1 },
  eyebrow: { color: tokens.colorBrandForeground1, fontSize: tokens.fontSizeBase100, fontWeight: tokens.fontWeightBold, textTransform: 'uppercase', letterSpacing: '0.04em' },
  subtitle: { color: tokens.colorNeutralForeground3 },
  kpis: { display: 'grid', gap: tokens.spacingHorizontalS, gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))' },
  kpi: { display: 'flex', flexDirection: 'column', gap: '2px', padding: '10px 12px', borderRadius: tokens.borderRadiusLarge, backgroundColor: tokens.colorNeutralBackground2 },
  kpiLabel: { color: tokens.colorNeutralForeground3, fontSize: tokens.fontSizeBase200 },
  kpiValue: { fontSize: tokens.fontSizeBase500, fontWeight: tokens.fontWeightSemibold, lineHeight: tokens.lineHeightBase500 },
  kpiNote: { color: tokens.colorNeutralForeground3, fontSize: tokens.fontSizeBase100 },
  danger: { color: tokens.colorPaletteRedForeground1 },
  warning: { color: tokens.colorPaletteDarkOrangeForeground1 },
  success: { color: tokens.colorPaletteGreenForeground1 },
  section: { display: 'flex', flexDirection: 'column', gap: tokens.spacingVerticalS },
  sectionTitle: { fontWeight: tokens.fontWeightSemibold },
  meter: { position: 'relative', height: '10px', borderRadius: '5px', backgroundColor: tokens.colorNeutralBackground4, overflow: 'hidden', minWidth: '60px' },
  meterActual: { position: 'absolute', top: 0, bottom: 0, left: 0, backgroundColor: tokens.colorBrandBackground },
  meterCommitted: { position: 'absolute', top: 0, bottom: 0, backgroundColor: tokens.colorBrandBackground2Pressed },
  meterOver: { backgroundColor: tokens.colorPaletteRedBackground3 },
  center: { display: 'flex', justifyContent: 'center', padding: '24px' },
  footer: { display: 'flex', flexWrap: 'wrap', gap: tokens.spacingHorizontalS },
});

export interface ShellProps {
  eyebrow: string;
  title: string;
  subtitle?: string;
  onRefresh?: () => void;
  children?: React.ReactNode;
}

export const Shell: React.FC<ShellProps> = props => {
  const s = useStyles();
  const { onRequestFullscreen } = useAgent();
  const t = strings().common;
  return (
    <div className={s.card}>
      <div className={s.accent} />
      <div className={s.body}>
        <div className={s.header}>
          <div className={s.heading}>
            <span className={s.eyebrow}>{props.eyebrow}</span>
            <Text size={500} weight="semibold">{props.title}</Text>
            {props.subtitle && <Text size={200} className={s.subtitle}>{props.subtitle}</Text>}
          </div>
          {props.onRefresh && (
            <Tooltip content={t.refresh} relationship="label">
              <Button appearance="subtle" icon={<ArrowClockwise20Regular />} onClick={props.onRefresh} />
            </Tooltip>
          )}
          {onRequestFullscreen && (
            <Tooltip content={t.expand} relationship="label">
              <Button appearance="subtle" icon={<ArrowMaximize20Regular />} onClick={onRequestFullscreen} />
            </Tooltip>
          )}
        </div>
        {props.children}
      </div>
    </div>
  );
};

export type Tone = 'neutral' | 'danger' | 'warning' | 'success';

export const Kpi: React.FC<{ label: string; value: string; note?: string; tone?: Tone }> = ({ label, value, note, tone }) => {
  const s = useStyles();
  return (
    <div className={s.kpi}>
      <span className={s.kpiLabel}>{label}</span>
      <span className={mergeClasses(s.kpiValue, tone && tone !== 'neutral' ? s[tone] : undefined)}>{value}</span>
      {note && <span className={s.kpiNote}>{note}</span>}
    </div>
  );
};

export const KpiGrid: React.FC<{ children?: React.ReactNode }> = ({ children }) => <div className={useStyles().kpis}>{children}</div>;

export const Section: React.FC<{ title: string; children?: React.ReactNode; action?: React.ReactNode }> = ({ title, children, action }) => {
  const s = useStyles();
  return (
    <div className={s.section}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Text className={s.sectionTitle}>{title}</Text>
        <span style={{ marginLeft: 'auto' }}>{action}</span>
      </div>
      {children}
    </div>
  );
};

export const Footer: React.FC<{ children?: React.ReactNode }> = ({ children }) => <div className={useStyles().footer}>{children}</div>;

const HEALTH_COLOR: Record<HealthLevel, 'danger' | 'warning' | 'success' | 'informative'> = {
  offTrack: 'danger', atRisk: 'warning', onTrack: 'success', notTracked: 'informative',
};

export const HealthBadge: React.FC<{ level: HealthLevel }> = ({ level }) => (
  <Badge appearance="tint" color={HEALTH_COLOR[level]}>{strings().health[level]}</Badge>
);

/** Actual and committed against budget; turns red past 100%. */
export const BudgetMeter: React.FC<{ budget: number; actual: number; committed?: number }> = ({ budget, actual, committed = 0 }) => {
  const s = useStyles();
  const total = Math.max(budget, actual + committed, 1);
  const over = actual + committed > budget;
  const label = strings().common.budgetMeter(Math.round(actual / (budget || 1) * 100), Math.round(committed / (budget || 1) * 100));
  return (
    <div className={s.meter} role="img" aria-label={label} title={label}>
      <div className={mergeClasses(s.meterActual, over && s.meterOver)} style={{ width: `${actual / total * 100}%` }} />
      <div className={s.meterCommitted} style={{ left: `${actual / total * 100}%`, width: `${committed / total * 100}%` }} />
    </div>
  );
};

export const Loading: React.FC<{ label?: string }> = ({ label }) => (
  <div className={useStyles().center}><Spinner size="small" label={label || strings().common.loading} /></div>
);

export const ErrorBar: React.FC<{ error: Error }> = ({ error }) => {
  const t = strings().common;
  if (error instanceof SettingsMissingError) {
    return (
      <MessageBar intent="warning">
        <MessageBarBody>
          <MessageBarTitle>{t.notConfiguredTitle}</MessageBarTitle>
          {t.notConfigured(ENVIRONMENT_URL_KEY)}
        </MessageBarBody>
      </MessageBar>
    );
  }
  const access = error instanceof DataverseError && (error.status === 401 || error.status === 403);
  return (
    <MessageBar intent="error">
      <MessageBarBody>
        <MessageBarTitle>{access ? t.noAccess : t.failed}</MessageBarTitle>
        {error.message}
      </MessageBarBody>
    </MessageBar>
  );
};

export const Info: React.FC<{ title?: string; children?: React.ReactNode; intent?: 'info' | 'warning' | 'success' | 'error' }> = props => (
  <MessageBar intent={props.intent || 'info'}>
    <MessageBarBody>
      {props.title && <MessageBarTitle>{props.title}</MessageBarTitle>}
      {props.children}
    </MessageBarBody>
  </MessageBar>
);

export const OpenInApp: React.FC<{ url: string; label?: string }> = ({ url, label }) => {
  const { openLink } = useAgent();
  return (
    <Button size="small" appearance="secondary" icon={<Open16Regular />} onClick={() => openLink(url)}>
      {label || strings().common.openInApp}
    </Button>
  );
};

export const FollowUp: React.FC<{ prompt: string; children?: React.ReactNode }> = ({ prompt, children }) => {
  const { followUp } = useAgent();
  return <Button size="small" appearance="subtle" onClick={() => followUp(prompt)}>{children}</Button>;
};

export const ToneText: React.FC<{ tone: Tone; children?: React.ReactNode }> = ({ tone, children }) => {
  const s = useStyles();
  return <span className={tone !== 'neutral' ? s[tone] : undefined}>{children}</span>;
};

/** Project picker shown when the project in the prompt is missing or matches several projects. */
export const Choices: React.FC<{ items: { key: string; label: string; prompt: string }[] }> = ({ items }) => {
  const s = useStyles();
  const { followUp } = useAgent();
  return (
    <div className={s.footer}>
      {items.map(i => <Button key={i.key} size="small" onClick={() => followUp(i.prompt)}>{i.label}</Button>)}
    </div>
  );
};
