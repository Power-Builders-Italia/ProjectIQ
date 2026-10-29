import * as React from 'react';
import { Badge, Button, makeStyles, Text, tokens } from '@fluentui/react-components';

import { useAgent } from '../AgentContext';
import { Info, Shell } from '../kit';
import { CATEGORY_TITLES, INTENTS, promptFor, type IntentCategory } from '../../intents';

const useStyles = makeStyles({
  grid: { display: 'grid', gap: tokens.spacingHorizontalS, gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' },
  card: { display: 'flex', flexDirection: 'column', gap: '4px', padding: '10px 12px', borderRadius: tokens.borderRadiusLarge, backgroundColor: tokens.colorNeutralBackground2 },
  prompt: { justifyContent: 'flex-start', textAlign: 'left', paddingLeft: 0 },
});

const OPERATION = { information: 'Read-only', review: 'Review → Confirm', submit: 'Draft → Review → Confirm' } as const;

export const ExploreView: React.FC = () => {
  const s = useStyles();
  const { followUp, setModelContext } = useAgent();
  React.useEffect(() => {
    setModelContext('ProjectIQ agent scenarios: ' + INTENTS.filter(i => i.category !== 'help').map(i => `${i.title}: ${i.summary}`).join('\n'));
  }, []);
  const categories = (Object.keys(CATEGORY_TITLES) as IntentCategory[]).filter(c => c !== 'help');
  return (
    <Shell eyebrow="ProjectIQ agent" title="What I can do" subtitle="Live ProjectIQ data, with your own permissions">
      {categories.map(c => (
        <div key={c}>
          <Text weight="semibold">{CATEGORY_TITLES[c]}</Text>
          <div className={s.grid}>
            {INTENTS.filter(i => i.category === c).map(i => (
              <div key={i.key} className={s.card}>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <Text weight="semibold">{i.title}</Text>
                  <Badge size="small" appearance="tint" color={i.operation === 'information' ? 'informative' : 'warning'}>{OPERATION[i.operation]}</Badge>
                </div>
                <Text size={200}>{i.summary}</Text>
                <Button className={s.prompt} size="small" appearance="transparent" onClick={() => followUp(promptFor(i.key, 'PRJ-000123'))}>
                  “{promptFor(i.key, 'PRJ-000123')}”
                </Button>
              </div>
            ))}
          </div>
        </div>
      ))}
      <Info>Only the hours you log and the hours you approve or reject are written, after you select Confirm. Purchases, orders and project changes stay in the ProjectIQ app.</Info>
    </Shell>
  );
};
