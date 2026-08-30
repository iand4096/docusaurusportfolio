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
        "title": "Suggest taxonomy with DeepSeek",
        "script": "./scripts/frontmatter_taxonomy.py",
        "command": "python",
        "type": "content"
      }
    ]
  };
};