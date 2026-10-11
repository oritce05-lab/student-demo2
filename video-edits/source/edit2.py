import json,sys
S=sys.argv[1]
END=41.73;PAD=0.12
gaps=[(7.88,8.24),(9.76,10.42),(17.82,18.64),(23.94,24.36),(27.68,28.08),(36.38,37.04)]
cuts=[(a+PAD,b-PAD) for a,b in gaps if b-a-2*PAD>0.08]
keep=[];s=0.0
for a,b in cuts: keep.append((s,a)); s=b
keep.append((s,END))
def m(t):
    r=0
    for a,b in cuts:
        if t>=b: r+=b-a
        elif t>a: r+=t-a
    return round(t-r,3)
lines=[(0.05,2.6,'אני סיימתי עכשיו קורס *AI Agents*'),(2.6,4.66,'ביחידה *ללימודי חוץ*'),
(4.66,7.88,'הגעתי לכאן בהמלצה של חבר'),(8.24,9.76,'ואני *מאוד מרוצה*'),
(10.42,13.0,'קודם כל, גם מהחומר שהעבירו לנו'),(13.0,15.0,'גם מהמרצה אלכס, שמאוד *מקצועי*'),(15.0,17.82,'מאוד *סבלני*, עם המון ידע טכני'),
(18.64,20.4,'וזה נתן לי *הרבה כלים*'),(20.4,22.5,'אני רוצה לבנות *אפליקציות* בעצמי'),(22.5,23.94,'למרות שאין לי רקע טכני'),
(24.36,26.2,'אני עושה דברים עם בן הזוג שלי'),(26.2,27.68,'ובונה *אוטומציות*'),
(28.08,30.6,'זה באמת נתן לי *המון כלים*'),(30.6,32.2,'כדי להתקדם'),
(32.2,34.4,'גם בעבודה, אני עושה את זה בעבודה'),(34.4,36.38,'או כדי להיות *עצמאית* אפילו'),
(37.04,39.3,'אז אני מאוד *ממליצה* על הקורס הזה'),(39.3,41.48,'ועל היחידה, ואני מודה לכולם')]
chips=[(1.4,4.6,'bot','AI Agents'),(5.3,7.88,'heart','בהמלצת חבר'),(13.9,17.82,'check','מקצועי'),(15.2,17.82,'check','סבלני'),
(20.9,23.94,'phone','אפליקציות'),(26.3,27.68,'gear','אוטומציות'),(34.5,36.38,'rocket','עצמאות'),(37.5,41.6,'stars','')]
data={'subs':[[m(a),m(b),t] for a,b,t in lines],'chips':[[m(a),m(b),i,t] for a,b,i,t in chips],'end':m(END)}
json.dump(data,open(S+'/timeline.json','w'),ensure_ascii=False)
# video: per segment upscale 2x, gentle continuous push-in (zoompan), alternate base zoom
fc=[]
for i,(a,b) in enumerate(keep):
    z0=1.0 if i%2==0 else 1.07;fr=int(round((b-a)*30))
    fc.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,fps=30,scale=2160:3840:flags=lanczos,zoompan=z='{z0}+0.025*on/{max(fr,1)}':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*0.35':d=1:s=1080x1920:fps=30,setsar=1[v{i}]")
    fc.append(f"[1:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.015,afade=t=out:st={b-a-0.015:.3f}:d=0.015[a{i}]")
n=len(keep)
fc.append(''.join(f'[v{i}][a{i}]' for i in range(n))+f'concat=n={n}:v=1:a=1[vc][ac]')
fc.append('[vc]tpad=stop_mode=clone:stop_duration=3.2[vout]');fc.append('[ac]apad=pad_dur=3.2[aout]')
open(S+'/fc2.txt','w').write(';\n'.join(fc))
print('cut duration',m(END),'total',round(m(END)+3.2,2))
