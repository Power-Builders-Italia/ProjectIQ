import { z } from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';

const propertiesSchema = z.object({
  supplier: z.string().optional().describe('Supplier name, when the user asks about one supplier.')
});

export type IGetSupplierComplianceProperties = z.infer<typeof propertiesSchema>;

export default zodToJsonSchema(propertiesSchema);
