import { z } from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';

const propertiesSchema = z.object({
  project: z.string().optional().describe('Project code (for example PRJ-000123) or name, as written by the user.')
});

export type IGetProjectBudgetProperties = z.infer<typeof propertiesSchema>;

export default zodToJsonSchema(propertiesSchema);
