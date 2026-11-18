import React from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import CodeBlock from '@theme/CodeBlock';
import TabItem from '@theme/TabItem';
import Tabs from '@theme/Tabs';
import {getEndpoint, searchApiUrl} from '../ApiEndpoint/operationLinks';

type ApiExampleProps = {
  operationId: string;
  example: string;
  status?: number;
  language?: string;
};

function shellQuote(value: string): string {
  return "'" + value.replaceAll("'", "'\"'\"'") + "'";
}

export default function ApiExample({operationId, example, status = 200, language}: ApiExampleProps): React.JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  const {method, path, operation} = getEndpoint(operationId);
  const request = operation.requestBody?.content?.['application/json']?.examples?.[example];
  if (!request) throw new Error(`Missing JSON request example "${example}" for "${operationId}".`);
  const requestJson = JSON.stringify(request.value, null, 2);

  const url = searchApiUrl(siteConfig.customFields) + path;
  const command = [
    `curl --request ${method.toUpperCase()} ${shellQuote(url)}`,
    "  --header 'Content-Type: application/json'",
    `  --data-raw ${shellQuote(requestJson)}`,
  ].join(' \\' + '\n');
  const curlExample = <CodeBlock language="bash" title="cURL">{command}</CodeBlock>;

  if (language === 'curl') return curlExample;

  if (language) {
    const matching = operation['x-codeSamples']?.filter(sample => sample.lang.toLowerCase() === language.toLowerCase());
    const sample = matching?.find(sample => sample.example === example) ?? matching?.find(sample => !sample.example);
    if (!sample) throw new Error(`Missing "${language}" code sample for "${operationId}" example "${example}".`);
    return <CodeBlock language={language.toLowerCase()} title={sample.label ?? sample.lang}>{sample.source}</CodeBlock>;
  }

  const response = operation.responses?.[status]?.content?.['application/json']?.examples?.[example];
  if (!response) throw new Error(`Missing HTTP ${status} JSON response example "${example}" for "${operationId}".`);

  return (
    <Tabs>
      <TabItem value="request" label="Request">
        <CodeBlock language="json">{requestJson}</CodeBlock>
        {curlExample}
      </TabItem>
      <TabItem value="response" label={`${status} response`}>
        <CodeBlock language="json">{JSON.stringify(response.value, null, 2)}</CodeBlock>
      </TabItem>
    </Tabs>
  );
}
