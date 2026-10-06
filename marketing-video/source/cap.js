const { chromium } = require('playwright');
const { spawn } = require('child_process');
const [,, html, out, mode, ...times] = process.argv;
(async()=>{
  const b = await chromium.launch();
  const p = await b.newPage({viewport:{width:1080,height:1920}});
  await p.addInitScript(()=>{window.__capture=true});
  await p.goto('file://'+html); await p.evaluate(()=>document.fonts.ready);
  if(mode==='stills'){
    for(const t of times){ await p.evaluate(t=>render(+t),t); await p.screenshot({path:`${out}/f_${t}.png`}); }
  } else {
    const fps=30, dur=await p.evaluate(()=>DUR);
    const ff=spawn('ffmpeg',['-y','-f','image2pipe','-framerate',''+fps,'-c:v','mjpeg','-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','18','-preset','medium','-movflags','+faststart',out],{stdio:['pipe','ignore','inherit']});
    for(let i=0;i<fps*dur;i++){ await p.evaluate(t=>render(t),i/fps); ff.stdin.write(await p.screenshot({type:'jpeg',quality:92})); }
    ff.stdin.end(); await new Promise(r=>ff.on('close',r));
  }
  await b.close();
})();
