const { chromium } = require('/opt/node-tools/node_modules/playwright');
const { spawn } = require('child_process');
const [,, html, out, mode, ...times] = process.argv;
(async()=>{
  const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1080,height:1920}});
  await p.goto('file://'+html); await p.evaluate(()=>document.fonts.ready);
  if(mode==='stills'){ for(const t of times){ await p.evaluate(t=>render(+t),t); await p.screenshot({path:`${out}/o_${t}.png`,omitBackground:true}); } }
  else { const fps=30,dur=await p.evaluate(()=>DUR);
    const ff=spawn('ffmpeg',['-y','-f','image2pipe','-framerate',''+fps,'-c:v','png','-i','-','-c:v','qtrle','-pix_fmt','argb',out],{stdio:['pipe','ignore','inherit']});
    for(let i=0;i<Math.round(fps*dur);i++){ await p.evaluate(t=>render(t),i/fps); ff.stdin.write(await p.screenshot({type:'png',omitBackground:true})); }
    ff.stdin.end(); await new Promise(r=>ff.on('close',r)); }
  await b.close();})();
