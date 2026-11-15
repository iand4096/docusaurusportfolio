import React from 'react';
import {Redirect, useLocation} from '@docusaurus/router';
import useBaseUrl from '@docusaurus/useBaseUrl';

// Keep older /browse links working; Explore is the only discovery page.
export default function BrowsePage(): React.JSX.Element {
  const exploreUrl = useBaseUrl('/explore');
  const {search, hash} = useLocation();
  // Preserve contentType (including repeated values) when redirecting old
  // home-page links into the unified Explore page.
  const params = new URLSearchParams(search);
  params.set('view', 'browse');
  return <Redirect to={`${exploreUrl}?${params.toString()}${hash}`} />;
}
