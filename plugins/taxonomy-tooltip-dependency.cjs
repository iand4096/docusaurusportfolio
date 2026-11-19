module.exports = function taxonomyTooltipDependency(source) {
  const {taxonomyPath, glossaryPath} = this.getOptions();
  this.addDependency(taxonomyPath);
  this.addDependency(glossaryPath);
  return source;
};
