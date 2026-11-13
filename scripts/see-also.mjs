import path from 'node:path';
import {createRequire} from 'node:module';
import {generate, writeArtifacts} from './lib/see-also.mjs';

const require = createRequire(import.meta.url);
const {loadSiteConfig} = require('@docusaurus/core/lib/server/config.js');
const action = process.argv[2] ?? 'generate';
if (!['generate', 'check'].includes(action)) throw new Error('Usage: node scripts/see-also.mjs generate|check');
const siteDir = path.resolve('.');
const {siteConfig} = await loadSiteConfig({siteDir});
const result = await generate(siteDir, siteConfig);
await writeArtifacts(siteDir, result, action === 'check');
console.log(`See also ${action === 'check' ? 'check passed' : 'generated'}: ${Object.values(result.index.pages).filter(page => page.links.length).length} pages with recommendations.`);
console.log('Review: reports/see-also.md');
