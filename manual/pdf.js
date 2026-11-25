const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + process.argv[2], { waitUntil: 'networkidle' });
  await p.pdf({ path: process.argv[3], width: '5.5in', height: '8.5in', printBackground: true, preferCSSPageSize: true });
  await b.close();
})();
