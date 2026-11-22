module.exports = function taxonomyTooltipDependency(source) {
  for (const dependency of this.getOptions().dependencies) this.addDependency(dependency);
  return source;
};
