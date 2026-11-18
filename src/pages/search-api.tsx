import React, {useEffect, useMemo, useRef, useState} from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import useBaseUrl from '@docusaurus/useBaseUrl';
import useBrokenLinks from '@docusaurus/useBrokenLinks';
import Layout from '@theme/Layout';
import {useColorMode} from '@docusaurus/theme-common';
import {operationAnchors, operationSlug, searchApiUrl, tagSlug} from '@site/src/components/ApiEndpoint/operationLinks';

type CreateReference = typeof import('@scalar/api-reference').createApiReference;
type ReferenceInstance = ReturnType<CreateReference>;
type ScalarGlobal = {createApiReference: CreateReference};

let renderer: Promise<ScalarGlobal> | undefined;

function loadRenderer(): Promise<ScalarGlobal> {
  renderer ??= new Promise<ScalarGlobal>((resolve, reject) => {
    const script = document.createElement('script');
    // Emit the locked npm distribution as a local asset instead of depending on a CDN.
    script.src = new URL('../../node_modules/@scalar/api-reference/dist/browser/standalone.js', import.meta.url).href;
    script.onload = () => {
      const scalar = (window as Window & {Scalar?: ScalarGlobal}).Scalar;
      if (scalar) resolve(scalar);
      else reject(new Error('The API reference renderer did not initialise.'));
    };
    script.onerror = () => reject(new Error('The API reference renderer could not be loaded.'));
    document.head.appendChild(script);
  });
  return renderer;
}

function SearchReference(): React.JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  const {colorMode} = useColorMode();
  const specUrl = useBaseUrl('/api/search-openapi.json');
  const mount = useRef<HTMLDivElement>(null);
  const instance = useRef<ReferenceInstance | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const apiUrl = searchApiUrl(siteConfig.customFields);
  const configuration = useMemo(() => ({
    url: specUrl,
    generateOperationSlug: operationSlug,
    generateTagSlug: tagSlug,
    servers: [{url: apiUrl}],
    hideTestRequestButton: true,
    hideClientButton: true,
    hideDarkModeToggle: true,
    showDeveloperTools: 'never' as const,
    showToolbar: 'never' as const,
    agent: {disabled: true},
    defaultOpenAllTags: true,
    withDefaultFonts: false,
    telemetry: false,
    darkMode: colorMode === 'dark',
  }), [apiUrl, colorMode, specUrl]);
  const latestConfiguration = useRef(configuration);

  useEffect(() => {
    latestConfiguration.current = configuration;
    instance.current?.updateConfiguration(configuration);
  }, [configuration]);

  useEffect(() => {
    let disposed = false;
    loadRenderer().then(scalar => {
      // The standalone script can finish loading after navigation. Its stylesheet
      // is injected at script execution, before any reference instance mounts.
      const stylesheet = document.querySelector<HTMLStyleElement>('style#scalar-style')?.sheet;
      if (stylesheet) stylesheet.disabled = disposed;
      if (disposed || !mount.current) return;
      instance.current = scalar.createApiReference(mount.current, latestConfiguration.current);
      setStatus('ready');
    }).catch(() => {
      if (!disposed) setStatus('error');
    });
    return () => {
      disposed = true;
      instance.current?.destroy();
      instance.current = null;
    };
  }, []);

  return (
    <main>
      {status === 'loading' && <p className="container margin-vert--md" role="status">Loading API reference…</p>}
      {status === 'error' && <p className="container margin-vert--md" role="alert">
        The API reference couldn’t load. <a href={specUrl}>Download the OpenAPI document</a>.
      </p>}
      <noscript><p className="container margin-vert--md"><a href={specUrl}>Download the OpenAPI document</a>.</p></noscript>
      <div ref={mount} />
    </main>
  );
}

export default function SearchApiPage(): React.JSX.Element {
  const {collectAnchor} = useBrokenLinks();
  // Scalar renders these anchors in the browser, after Docusaurus checks links.
  operationAnchors.forEach(collectAnchor);
  return (
    <Layout title="Search API reference" description="OpenAPI reference for the Portfolio Governed Knowledge API.">
      <SearchReference />
    </Layout>
  );
}
