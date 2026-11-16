'use strict';
// Match known coding families in the model name, never an unrelated tag.
function isCodingModel(name) {
  const family=String(name).toLowerCase().split(':')[0].split('/').pop();
  return /(?:^|[-_.])(?:coder|codellama|starcoder\d*|codegemma|codestral|devstral|granite-code|codeqwen|wizardcoder|opencoder|stable-code|replit-code)(?:$|[-_.\d])/.test(family);
}
function chooseCodingModel(installed, preferred) {
  const candidates=installed.filter(isCodingModel);
  return candidates.includes(preferred)?preferred:(candidates[0]||null);
}
if(typeof module!=='undefined')module.exports={isCodingModel,chooseCodingModel};
