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

  // Enable Mermaid diagrams in Markdown and MDX files.
  markdown: {
    mermaid: true,
  },

  stylesheets: [
    {
      href: 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    },
  ],

  themes: ['@docusaurus/theme-mermaid'],

plugins: [
  [
    '@docusaurus/plugin-client-redirects',
    {
      redirects: [
        {
          from: '/docs/AMXInspiredSignageComposer',
          to: '/docs/case-studies/AMXInspiredSignageComposer',
        },
        {
          from: '/docs/MasterpassMerchantIntegrationGuide',
          to: '/docs/case-studies/MasterpassMerchantIntegrationGuide',
        },
        {
          from: '/docs/MDES4Merchants',
          to: '/docs/case-studies/MDES4Merchants',
        }
      ],
    },
  ],
],

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
        },

        blog: {
          showReadingTime: true,

          feedOptions: {
            type: ['rss', 'atom'],
            xslt: true,
          },

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

    mermaid: {
      theme: {
        light: 'neutral',
        dark: 'dark',
      },

      options: {
        fontSize: 22,

        flowchart: {
          useMaxWidth: true,
          htmlLabels: true,
          nodeSpacing: 40,
          rankSpacing: 50,
        },
      },
    },

    navbar: {
      title: 'Home',

      items: [
        {
          label: 'Case studies',
          to: '/docs/case-studies/scalingdeveloperdocs',
          position: 'left',
          activeBasePath: '/docs/case-studies',
        },
        {
          label: 'Skills',
          to: '/docs/skills',
          position: 'left',
          activeBasePath: '/docs',
        },
            {
          label: 'Tools',
          to: '/docs/tools',
          position: 'left',
          activeBasePath: '/docs',
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
              to: '/docs/case-studies/scalingdeveloperdocs',
            },
            {
              label: 'Skills',
              to: '/docs/skills',
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