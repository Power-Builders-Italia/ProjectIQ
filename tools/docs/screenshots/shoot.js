// Opens page.html once per control and saves a screenshot of it (called by screenshots.py).
const path = require('path');
const { chromium } = require('playwright');
const [out, ...controls] = process.argv.slice(2);
(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 1220, height: 700 }, deviceScaleFactor: 2 });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    for (const c of controls) {
        await page.goto('file://' + path.join(__dirname, 'page.html') + '?c=' + c);
        await page.waitForTimeout(1500);
        await (await page.$('#root')).screenshot({ path: path.join(out, c + '.raw.png') });
    }
    await browser.close();
    if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
})();
