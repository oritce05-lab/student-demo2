import numpy as np, wave, sys
sr=44100; D=29.5; N=int(sr*D); t=np.arange(N)/sr
out=np.zeros((N,2))
def note(f): return 440*2**((f-69)/12)
def add(sig,start,ch=(1,1)):
    i=int(start*sr); n=min(len(sig),N-i)
    out[i:i+n,0]+=sig[:n]*ch[0]; out[i:i+n,1]+=sig[:n]*ch[1]
bpm=120; beat=60/bpm
# chord progression Am F C G, 2s each
prog=[[57,60,64],[53,57,60],[48,55,64],[55,59,62]]
for k in range(15):
    s=k*2.0; ch=prog[k%4]; L=2.2; tt=np.arange(int(L*sr))/sr
    env=np.minimum(tt/0.25,1)*np.exp(-tt*0.6)*np.minimum((L-tt)/0.2,1)
    for j,m in enumerate(ch):
        f=note(m)
        w=sum(np.sin(2*np.pi*f*h*tt+0.3*j)/h**1.6 for h in range(1,6))
        det=np.sin(2*np.pi*f*1.004*tt)
        add(0.05*env*(w+0.4*det),s,(1-0.2*j,0.6+0.2*j))
    # bass
    fb=note(ch[0]-12); add(0.10*env*np.sin(2*np.pi*fb*tt),s)
# arpeggio pluck from 7.2s
for i in range(int((D-7.2)/ (beat/2))):
    s=7.2+i*beat/2
    if s>27.5: break
    ch=prog[int(s//2)%4]; m=ch[i%3]+12; tt=np.arange(int(0.3*sr))/sr
    add(0.045*np.exp(-tt*14)*np.sin(2*np.pi*note(m)*tt),s,(0.7,1) if i%2 else (1,0.7))
# kick + hat from 3.6s
def kick():
    tt=np.arange(int(0.35*sr))/sr; f=50+90*np.exp(-tt*30)
    return 0.5*np.exp(-tt*9)*np.sin(2*np.pi*np.cumsum(f)/sr)
rng=np.random.default_rng(1)
def hat():
    tt=np.arange(int(0.06*sr))/sr; n=rng.standard_normal(len(tt)); n=np.diff(n,prepend=0)
    return 0.05*np.exp(-tt*60)*n
b=3.25
while b<27.0:
    add(kick(),b); add(hat(),b+beat/2); b+=beat
# riser in hook 0-3.6
tt=t[:int(3.25*sr)]; n=rng.standard_normal(len(tt)); 
from numpy import convolve
n=convolve(n,np.ones(8)/8,'same')
add(0.12*(tt/3.25)**2*n,0)
sw=np.sin(2*np.pi*np.cumsum(200+600*(tt/3.25)**2)/sr); add(0.05*(tt/3.25)**2*sw,0)
# whooshes at transitions
for x in [3.25,5.3,12.0,16.3,19.1,22.5]:
    L=0.6; tt=np.arange(int(L*sr))/sr; n=convolve(rng.standard_normal(len(tt)),np.ones(12)/12,'same')
    env=np.sin(np.pi*tt/L)**2; add(0.12*env*n,x-L/2)
# end hit
tt=np.arange(int(4*sr))/sr; env=np.exp(-tt*1.2)
add(0.15*env*sum(np.sin(2*np.pi*note(m)*tt) for m in [45,57,60,64,69]),22.5)
# fade out
fo=np.minimum((D-t)/1.5,1)[:,None]; out*=fo
out/=np.max(np.abs(out))*1.12
with wave.open(sys.argv[1],'w') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((out*32767).astype('<i2').tobytes())
