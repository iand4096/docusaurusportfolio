/** A flow-level MDX endpoint occupies its own block. */
function inferApiEndpointVariant() {
  function visit(node) {
    if (node.type === 'mdxJsxFlowElement' && node.name === 'ApiEndpoint'
      && !node.attributes.some(attribute => attribute.name === 'variant')) {
      node.attributes.push({type: 'mdxJsxAttribute', name: 'variant', value: 'standalone'});
    }
    node.children?.forEach(visit);
  }
  return visit;
}

module.exports = {inferApiEndpointVariant};
