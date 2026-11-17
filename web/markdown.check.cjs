// Run with `npm test`: hostile markdown must reach the page as text, never as a live tag.
const { renderToStaticMarkup } = require("react-dom/server");
const { createElement } = require("react");
const { Markdown } = require("./node_modules/.cache/ui.cjs");

const hostile = [
  "Notes <kbd>see <img/src=x onerror=alert(1)> <base/href=//evil.example/>",
  "| a<code> <svg/onload=1> |\n|---|\n| <pre><form/action=//evil.example> |",
  "- item <script>x <iframe/src=//evil.example>",
  "<b>bold</b> ![image](https://evil.example/x.png)",
].join("\n\n");
const html = renderToStaticMarkup(createElement(Markdown, { text: `${hostile}\n\nR&amp;D & **ok**` }));
const live = html.match(/<(?!\/?(div|p|table|thead|tbody|tr|th|td|ul|li|strong)\b)[^>]*>/);
if (live) throw new Error(`live tag in the rendered markdown: ${live[0]}`);
if (!html.includes("R&amp;D &#38; <strong>ok</strong>")) throw new Error(`entities changed: ${html}`);
console.log("markdown: hostile input rendered as text");
