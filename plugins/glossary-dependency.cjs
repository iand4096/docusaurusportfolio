module.exports = function glossaryDependency(source) {
  this.addDependency(this.getOptions().glossaryPath);
  return source;
};
