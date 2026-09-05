import fs from 'node:fs/promises';import path from 'node:path';import {createRequire} from 'node:module';import {pathToFileURL} from 'node:url';
const runtime=process.env.RUNTIME_ROOT;if(!runtime)throw Error('Set RUNTIME_ROOT');
const require=createRequire(path.join(runtime,'dependencies/node/node_modules/package.json'));
const {FileBlob,PresentationFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const [source,dest,slideNumber,oldText,newText]=process.argv.slice(2);
if(!newText||source===dest)throw Error('Usage: edit.mjs source.pptx NEW-output.pptx slide-number old-title new-title');
try{await fs.access(dest);throw Error('Output already exists')}catch(e){if(e.code!=='ENOENT')throw e}
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const snapshot=await p.inspect({kind:'slide,textbox',maxChars:1000000});
const records=snapshot.ndjson.trim().split('\n').map(s=>JSON.parse(s));
const owner=records.find(r=>r.kind==='slide'&&r.slide===Number(slideNumber));
if(!owner||owner.title!==oldText)throw Error('Slide title did not match; inspect the source before editing');
// The title is the first text box in these tested fixtures. Fail closed if no text box exists.
const record=records.find(r=>r.kind==='textbox'&&r.slide===Number(slideNumber));
if(!record)throw Error('No title text box');
p.resolve(record.id).text.replace(oldText,newText);
const checked=(await p.inspect({kind:'slide',maxChars:1000000})).ndjson.trim().split('\n').map(JSON.parse);
if(!checked.some(r=>r.kind==='slide'&&r.slide===Number(slideNumber)&&r.title===newText))throw Error('Title edit verification failed');
await(await PresentationFile.exportPptx(p)).save(dest);
await fs.writeFile(dest+'.inspect.ndjson',(await p.inspect({kind:'slide,textbox',maxChars:1000000})).ndjson);
console.log('Exported edit candidate; render and compare before use: '+dest);
