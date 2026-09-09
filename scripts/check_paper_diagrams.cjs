/* Headless rendered-label regression check; PLAYWRIGHT_MODULE may select a local installation. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || '/home/ff/Projects/StatePort/apps/web/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.PAPER_BASE || 'http://127.0.0.1:4194';
const out=process.env.PAPER_REPORT || 'output/diagram-clipping-20260909/local';
const stem='stateware-whitepaper-public-v1-1';
const normalize=s=>s.replace(/\s+/g,' ').trim();
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const results=[];
 try {
 for(const width of [360,768,1440]) for(const javaScriptEnabled of [true,false]) {
  const context=await browser.newContext({viewport:{width,height:1000},javaScriptEnabled});
  const page=await context.newPage();
  await page.goto(`${base}/papers/stateware-whitepaper-public-v1.1.html`);
  for(let i=1;i<=10;i++) {
   const figure=page.locator(`#figure-${i}`);await figure.scrollIntoViewIfNeeded();
   const img=figure.locator('img');await img.evaluate(e=>e.decode());
   const embedded=await img.evaluate(e=>({loaded:e.complete&&e.naturalWidth>0,width:e.width,natural:e.naturalWidth}));
   const scroll=figure.locator('.paper-diagram-scroll');
   await figure.screenshot({path:`${out}/embedded-${width}-${javaScriptEnabled}-${i}.png`});
   await scroll.evaluate(e=>e.scrollLeft=e.scrollWidth);
   if(await scroll.evaluate(e=>e.scrollWidth>e.clientWidth)) await figure.screenshot({path:`${out}/embedded-right-${width}-${javaScriptEnabled}-${i}.png`});
   results.push({kind:'embedded',width,javaScriptEnabled,i,...embedded,overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});
  }
  for(let i=1;i<=10;i++) {
   const id=`${stem}-${String(i).padStart(2,'0')}`;
   const response=await page.goto(`${base}/assets/diagrams/paper/${id}.svg`);if(!response.ok())throw Error('SVG request failed');
   const source=fs.readFileSync(path.join('assets/diagrams/src/paper',id+'.mmd'),'utf8');
   const expected=[...source.matchAll(/"([^"]+)"/g)].map(m=>normalize(m[1]));
   const inspect=()=>page.evaluate(()=>{
    const root=document.querySelector('svg');const bounds=root.getBoundingClientRect();
    const inside=(r,b)=>r.left>=b.left-1&&r.right<=b.right+1&&r.top>=b.top-1&&r.bottom<=b.bottom+1;
    return {foreignObjects:document.querySelectorAll('foreignObject').length,
     labels:[...document.querySelectorAll('.node text,.edgeLabel text')].map(e=>{
      const r=e.getBoundingClientRect();const node=e.closest('.node');const shape=node?.querySelector('.label-container');
      const text=[...e.querySelectorAll('.text-outer-tspan')].map(t=>t.textContent).join(' ')||e.textContent;
      return {text:text.replace(/\s+/g,' ').trim(),inViewport:inside(r,bounds),inNode:shape?inside(r,shape.getBoundingClientRect()):true};
     })};
   });
   const normal=await inspect();
   const actual=normal.labels.map(l=>l.text);
   const missing=expected.filter(t=>!actual.includes(t));
   await page.locator('svg').screenshot({path:`${out}/direct-${width}-${javaScriptEnabled}-${i}.png`});
   // Stress the original failure: wider locally installed font, same generated geometry.
   await page.evaluate(()=>{const style=document.createElementNS('http://www.w3.org/2000/svg','style');style.textContent='#my-svg,#my-svg .label,#my-svg svg {font-family:"Noto Sans" !important}';document.documentElement.append(style)});
   const alternateFont=await inspect();
   if(width===1440&&javaScriptEnabled)await page.locator('svg').screenshot({path:`${out}/font-stress-${i}.png`});
   results.push({kind:'direct',width,javaScriptEnabled,i,missing,normal,alternateFont});
  }
  await context.close();
 }
 }finally{await browser.close()}
 const failures=results.filter(r=>r.kind==='embedded'?(!r.loaded||r.overflow):(r.missing.length||[r.normal,r.alternateFont].some(s=>s.foreignObjects||s.labels.some(l=>!l.inViewport||!l.inNode))));
 fs.writeFileSync(`${out}/report.json`,JSON.stringify({base,results,failures},null,2));
 console.log(JSON.stringify({checks:results.length,failures},null,2));if(failures.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
