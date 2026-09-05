import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
// Use the supplied presentation runtime; keep its dependencies unchanged.
const runtime = process.env.RUNTIME_ROOT;
if (!runtime) throw Error('Set RUNTIME_ROOT to the supplied codex-primary-runtime directory');
const modules = path.join(runtime,'dependencies/node/node_modules');
const require = createRequire(path.join(modules,'package.json'));
const {Presentation,PresentationFile} = await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const root = path.resolve(import.meta.dirname,'..');
const source = path.resolve(process.argv[2] || path.join(import.meta.dirname,'deck.json'));
const workspaceDir = path.resolve(process.argv[3] || path.join(root,'../.local/stateport-slides'));
const data = JSON.parse(await fs.readFile(source,'utf8'));
const build = path.join(workspaceDir,'build'); const output=path.join(workspaceDir,'output');
await fs.mkdir(build,{recursive:true});await fs.mkdir(output,{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}});
const font='DejaVu Sans';
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const sections=[];
for (const [i,d] of data.slides.entries()) {
 const slide=p.slides.add();slide.background.fill='#F5F0E8';
 const text=(value,x,y,w,h,size,bold=false,color='#172B35')=>{
  const sh=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=value;sh.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none'};return sh;
 };
 text(d.title,64,50,1120,135,48,true);
 text(d.body,64,225,d.image?445:1080,270,29);
 text(`${i+1} / ${data.slides.length}   ·   StatePort sample · 5 September 2026`,64,658,1100,32,16);
 let img='';
 if(d.image){const bytes=await fs.readFile(path.join(root,'assets/media',d.image));slide.images.add({blob:bytes,contentType:'image/png',alt:d.title,fit:'contain',position:{left:565,top:205,width:650,height:406}});img=`<img alt="${escape(d.title)}" src="data:image/png;base64,${bytes.toString('base64')}">`;}
 if(d.link)text(d.link,64,515,1110,70,23,false,'#146168');
 slide.speakerNotes.textFrame.setText(`${d.note}\nSources: https://lennertvhoy.github.io/StatePort-Site/tutorials/site-orientation.html and https://lennertvhoy.github.io/StatePort-Site/releases/`);
 sections.push(`<section id="slide-${i+1}" aria-label="Slide ${i+1}"><h1>${escape(d.title)}</h1><div class="content"><p>${escape(d.body)}${d.link?`<br><a href="${escape(d.link)}">Open the field guide</a>`:''}</p>${img}</div><footer>${i+1} / ${data.slides.length} · StatePort sample · 5 September 2026</footer><details><summary>Speaker notes and limits</summary>${escape(d.note)}</details></section>`);
}
const candidate=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
const skill=process.env.PRESENTATIONS_SKILL;
if(!skill)throw Error('Set PRESENTATIONS_SKILL to the installed presentation skill directory');
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')));
await finalizePresentation({workspaceDir,candidatePath:candidate,finalPath:path.join(output,'stateport-introduction.pptx'),pythonExecutable:path.join(runtime,'dependencies/python/bin/python3'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json')});
await fs.writeFile(path.join(output,'stateport-introduction.html'),`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escape(data.title)}</title><style>
[hidden]{display:none!important}*{box-sizing:border-box}body{margin:0;background:#172B35;color:#172B35;font-family:"DejaVu Sans",sans-serif}section{position:relative;background:#F5F0E8;margin:1rem auto;padding:3rem;width:min(100%,1280px);min-height:720px}h1{font-size:clamp(30px,4vw,48px);margin:0 0 3rem;max-width:1120px}.content{display:flex;align-items:center;gap:3rem}.content p{font-size:clamp(20px,2.3vw,29px);line-height:1.45;flex:1}.content img{width:55%;height:406px;object-fit:contain}footer{margin-top:2rem;font-size:16px}details{margin-top:1rem}a{color:#146168}nav{position:sticky;top:0;z-index:1;padding:10px;background:#172B35;color:white;display:flex;gap:12px;align-items:center}button{font:inherit;padding:8px 16px}body.presenting section{display:none}body.presenting section.active{display:block}body.presenting{overflow:auto}section:focus{outline:3px solid #146168}@media(max-width:700px){section{padding:24px;min-height:0}.content{display:block}.content img{width:100%;height:auto;max-height:400px}h1{margin-bottom:24px}}@media print{nav,details{display:none}section,body.presenting section{display:block!important;break-after:page;margin:0;width:100%;height:100vh}}@page{size:landscape;margin:0}</style><body><nav hidden><button id="previous">Previous</button><button id="next">Next</button><button id="mode">Show all</button><button id="fullscreen">Fullscreen</button><span id="counter" aria-live="polite"></span></nav>${sections.join('')}<script>
const slides=[...document.querySelectorAll('section')];let index=0;const counter=document.querySelector('#counter');
function go(n){index=Math.max(0,Math.min(slides.length-1,Number.isFinite(n)?Math.trunc(n):0));slides.forEach((s,i)=>s.classList.toggle('active',i===index));counter.textContent=(index+1)+' / '+slides.length;history.replaceState(null,'','#slide-'+(index+1));return index;}
window.stateportDeck={go,next:()=>go(index+1),previous:()=>go(index-1),get index(){return index},get count(){return slides.length}};
document.querySelector('nav').hidden=false;document.body.classList.add('presenting');go(Number(location.hash.replace('#slide-',''))-1);
document.querySelector('#next').onclick=()=>go(index+1);document.querySelector('#previous').onclick=()=>go(index-1);document.querySelector('#mode').onclick=e=>{document.body.classList.toggle('presenting');e.target.textContent=document.body.classList.contains('presenting')?'Show all':'Present'};
document.querySelector('#fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen()}catch{counter.textContent='Fullscreen unavailable; use presentation view'}};
document.addEventListener('keydown',e=>{if(e.target.closest('button,a,summary'))return;if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();go(index+1)}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();go(index-1)}if(e.key==='Home')go(0);if(e.key==='End')go(slides.length-1)});
</script></body></html>`);
console.log(output);
