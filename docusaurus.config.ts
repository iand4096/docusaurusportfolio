import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This file runs in Node.js.
// Do not use browser APIs or JSX here.

const config: Config = {
  title: 'Ian Drewett | Technical Writing Portfolio',

  tagline:
    'Technical writer specialising in API documentation, payment integrations, and developer experience',

  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  // GitHub Pages deployment
  url: 'https://iand4096.github.io',
  baseUrl: '/docusaurusportfolio/',

  organizationName: 'iand4096',
  projectName: 'docusaurusportfolio',

  trailingSlash: false,
  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',

          // No editUrl:
          // portfolio visitors do not need "Edit this page" links.
        },

        blog: {
          showReadingTime: true,

          feedOptions: {
            type: ['rss', 'atom'],
            xslt: true,
          },

          // No editUrl here either.
          onInlineTags: 'warn',
          onInlineAuthors: 'warn',
          onUntruncatedBlogPosts: 'warn',
        },

        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },

    navbar: {
      title: 'Ian Drewett',

      // Do not use the default Docusaurus logo.
      // Add a logo property later only if you create your own logo.

      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: 'Case studies',
        },
        {
          href: 'https://www.linkedin.com/in/ian-drewett/',
          label: 'LinkedIn',
          position: 'right',
        },
        {
          href: 'https://github.com/iand4096/docusaurusportfolio',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },

    footer: {
      style: 'dark',

      links: [
        {
          title: 'Portfolio',
          items: [
            {
              label: 'Home',
              to: '/',
            },
            {
              label: 'Case studies',
              to: '/docs/Intro',
            },
          ],
        },
        {
          title: 'Professional profiles',
          items: [
            {
              label: 'LinkedIn',
              href: 'https://www.linkedin.com/in/ian-drewett/',
            },
            {
              label: 'GitHub',
              href: 'https://github.com/iand4096/docusaurusportfolio',
            },
          ],
        },
      ],

      copyright: `Copyright © ${new Date().getFullYear()} Ian Drewett. Built with Docusaurus.`,
    },

    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;