// Wrap the theme content so every documentation page exposes its Markdown export.
import React, {type ReactNode} from 'react';
import Content from '@theme-original/DocItem/Content';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import type {Props} from '@theme/DocItem/Content';
import DocMarkdownActions from '@site/src/components/DocMarkdownActions';
import SeeAlso from '@site/src/components/SeeAlso';

export default function DocItemContentWrapper(props: Props): ReactNode {
  const {metadata} = useDoc();
  return <>
    <DocMarkdownActions key={metadata.permalink} permalink={metadata.permalink} />
    <Content {...props} />
    <SeeAlso permalink={metadata.permalink} />
  </>;
}
