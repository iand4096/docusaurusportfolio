import spec from '@site/static/api/search-openapi.json';

const methods = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'] as const;
type HttpMethod = (typeof methods)[number];
type JsonMedia = {schema?: unknown; examples?: Record<string, {value: unknown}>};
type MediaExamples = {description?: string; content?: Record<string, JsonMedia>};
type Operation = {
  operationId?: string;
  tags?: readonly string[];
  summary?: string;
  requestBody?: MediaExamples;
  responses?: Record<string, MediaExamples>;
  'x-codeSamples'?: readonly {lang: string; source: string; label?: string; example?: string}[];
};
type Endpoint = {method: HttpMethod; path: string; fragment: string; operation: Operation};

export function tagSlug({name = ''}: {name?: string}): string {
  return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-');
}

export function operationSlug({operationId, method, path}: {operationId?: string; method: string; path: string}): string {
  return operationId ?? `${method}${path}`;
}

const operations = new Map<string, Endpoint>();
const paths: Record<string, Partial<Record<HttpMethod, Operation>>> = spec.paths;
for (const [path, entry] of Object.entries(paths)) {
  for (const method of methods) {
    const operation = entry[method];
    const operationId = operation?.operationId;
    const tag = operation?.tags?.[0];
    if (!operationId || !tag) continue;
    if (operations.has(operationId)) throw new Error(`Duplicate OpenAPI operation ID "${operationId}".`);
    operations.set(operationId, {
      method,
      path,
      operation,
      fragment: `#tag/${tagSlug({name: tag})}/${operationSlug({operationId, method, path})}`,
    });
  }
}

export const operationAnchors = Array.from(operations.values(), ({fragment}) => fragment.slice(1));

export function getEndpoint(operationId: string): Endpoint {
  const endpoint = operations.get(operationId);
  if (!endpoint) throw new Error(`OpenAPI operation "${operationId}" has no reference link.`);
  return endpoint;
}


export function searchApiUrl(customFields: Record<string, unknown> | undefined): string {
  return typeof customFields?.ragApiUrl === 'string'
    ? customFields.ragApiUrl : 'http://localhost:8000';
}
