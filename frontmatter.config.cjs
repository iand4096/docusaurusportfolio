const path = require("path");
const { existsSync } = require("fs");

module.exports = async (config) => {
  const windows = process.platform === "win32";
  const localPython = path.join(
    __dirname, ".venv", windows ? "Scripts" : "bin", windows ? "python.exe" : "python3"
  );
  const pythonCommand = existsSync(localPython) ? localPython : windows ? "python" : "python3";
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
        "command": pythonCommand,
        "type": "content"
      },
      {
        "id": "apply-taxonomy-review",
        "title": "Apply reviewed taxonomy metadata",
        "script": "./scripts/frontmatter_taxonomy_apply.py",
        "command": pythonCommand,
        "type": "content"
      },
      {
        "id": "generate-taxonomy-migration",
        "title": "Generate draft taxonomy migration",
        "script": "./scripts/frontmatter_taxonomy_migration.py",
        "command": pythonCommand,
        "type": "content"
      }
    ]
  };
};
