const path = require("path");

module.exports = async (config) => {
  const generated = require(
    path.join(
      __dirname,
      ".frontmatter",
      "generated-taxonomy.json"
    )
  );

  return {
    ...config,

    "frontMatter.framework.id": "Docusaurus",

    "frontMatter.taxonomy.customTaxonomy":
      generated.customTaxonomy,

    "frontMatter.taxonomy.contentTypes":
      generated.contentTypes,

    "frontMatter.custom.scripts": [
      {
        "id": "suggest-taxonomy-deepseek",
        "title": "Review metadata with DeepSeek",
        "script": "./scripts/frontmatter_taxonomy.py",
        "command": "python",
        "type": "content"
      },
      {
        "id": "apply-taxonomy-review",
        "title": "Apply reviewed taxonomy metadata",
        "script": "./scripts/frontmatter_taxonomy_apply.py",
        "command": "python",
        "type": "content"
      }
    ]
  };
};