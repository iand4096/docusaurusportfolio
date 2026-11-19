import {readdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import matter from 'gray-matter';
import {createSnippetResolver, serializeSourceSnippets} from '../plugins/source-snippets.cjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const pageDirectories = ['docs', 'blog', 'src/pages'];
const output = 'joined-pages.md';

async function findPages(directory) {
  const entries = await readdir(path.join(root, directory), {withFileTypes: true});
  const pages = [];
  for (const entry of entries) {
    const relative = path.posix.join(directory, entry.name);
    if (entry.isDirectory()) {
      pages.push(...await findPages(relative));
    } else if (entry.isFile() && /\.mdx?$/i.test(entry.name)
        && !/^readme\.mdx?$/i.test(entry.name)) {
      pages.push(relative);
    }
  }
  return pages;
}

const pages = (await Promise.all(pageDirectories.map(findPages))).flat().sort();
const sections = [];
const resolveSnippet = createSnippetResolver();
for (const page of pages) {
  const {data, content} = matter(await readFile(path.join(root, page), 'utf8'));
  const types = Array.isArray(data.type) ? data.type : [data.type];
  if (types.includes('landing-page')) continue;

  const title = data.title ?? path.posix.basename(page, path.posix.extname(page));
  sections.push(`# ${title}\n\n<!-- Source: ${page} -->\n\n${serializeSourceSnippets(content, resolveSnippet).trim()}`);
}

await writeFile(path.join(root, output), sections.join('\n\n---\n\n') + '\n');
console.log(`Exported ${sections.length} pages to ${output}`);
