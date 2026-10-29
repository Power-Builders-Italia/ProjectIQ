import * as React from 'react';
import { Badge, Button, makeStyles, Text, tokens } from '@fluentui/react-components';

import { useAgent } from '../AgentContext';
import { Info, Shell } from '../kit';
import { CATEGORIES, INTENTS, promptFor } from '../../intents';
import { EN, strings } from '../../i18n';

const useStyles = makeStyles({
  grid: { display: 'grid', gap: tokens.spacingHorizontalS, gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' },
  card: { display: 'flex', flexDirection: 'column', gap: '4px', padding: '10px 12px', borderRadius: tokens.borderRadiusLarge, backgroundColor: tokens.colorNeutralBackground2 },
  prompt: { justifyContent: 'flex-start', textAlign: 'left', paddingLeft: 0 },
});

export const ExploreView: React.FC = () => {
  const s = useStyles();
  const { followUp, setModelContext } = useAgent();
  const t = strings();
  React.useEffect(() => {
    setModelContext('ProjectIQ agent scenarios: ' + INTENTS.filter(i => i.category !== 'help')
      .map(i => `${EN.intents[i.key].title}: ${EN.intents[i.key].summary}`).join('\n'));
  }, []);
  const categories = CATEGORIES.filter(c => c !== 'help');
  return (
    <Shell eyebrow={t.explore.eyebrow} title={t.intents.ExploreAgentCapabilities.title} subtitle={t.explore.subtitle}>
      {categories.map(c => (
        <div key={c}>
          <Text weight="semibold">{t.categories[c]}</Text>
          <div className={s.grid}>
            {INTENTS.filter(i => i.category === c).map(i => (
              <div key={i.key} className={s.card}>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <Text weight="semibold">{t.intents[i.key].title}</Text>
                  <Badge size="small" appearance="tint" color={i.operation === 'information' ? 'informative' : 'warning'}>{t.explore[i.operation]}</Badge>
                </div>
                <Text size={200}>{t.intents[i.key].summary}</Text>
                <Button className={s.prompt} size="small" appearance="transparent" onClick={() => followUp(promptFor(i.key, 'PRJ-000123'))}>
                  “{promptFor(i.key, 'PRJ-000123')}”
                </Button>
              </div>
            ))}
          </div>
        </div>
      ))}
      <Info>{t.explore.writes}</Info>
    </Shell>
  );
};
