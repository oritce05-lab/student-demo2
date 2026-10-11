import numpy as np,wave,sys
sr=44100;D=float(sys.argv[2]);N=int(sr*D);out=np.zeros((N,2))
note=lambda m:440*2**((m-69)/12)
def add(sig,st,pan=(1,1)):
    i=int(st*sr);n=min(len(sig),N-i)
    if n>0: out[i:i+n,0]+=sig[:n]*pan[0];out[i:i+n,1]+=sig[:n]*pan[1]
bpm=96;beat=60/bpm;bar=4*beat
prog=[[60,64,67,71],[57,60,64,67],[65,69,72,76],[67,71,74,77]]  # Cmaj7 Am7 Fmaj7 G7-ish
k=0;t=0.0
while t<D:
    ch=prog[k%4];L=bar+0.4;tt=np.arange(int(L*sr))/sr
    env=np.minimum(tt/0.6,1)*np.minimum((L-tt)/0.5,1)
    for j,m in enumerate(ch):
        f=note(m-12);s=sum(np.sin(2*np.pi*f*h*tt+j)/h**2 for h in range(1,5))
        add(0.035*env*(s+0.5*np.sin(2*np.pi*f*1.003*tt)),t,(0.8+0.1*j,1-0.1*j))
    add(0.06*env*np.sin(2*np.pi*note(ch[0]-24)*tt),t)
    # soft pluck arpeggio (8ths)
    for i in range(8):
        st=t+i*beat/2;m=ch[[0,2,1,3,2,1,3,2][i]]+12;u=np.arange(int(0.5*sr))/sr
        add(0.03*np.exp(-u*7)*(np.sin(2*np.pi*note(m)*u)+0.3*np.sin(4*np.pi*note(m)*u)),st,(1,0.6) if i%2 else (0.6,1))
    # light shaker on offbeats
    rng=np.random.default_rng(k)
    for i in range(8):
        u=np.arange(int(0.05*sr))/sr;nz=np.diff(rng.standard_normal(len(u)),prepend=0)
        add((0.012 if i%2 else 0.007)*np.exp(-u*80)*nz,t+i*beat/2)
    t+=bar;k+=1
fi=np.minimum(np.arange(N)/sr/1.0,1);fo=np.minimum((D-np.arange(N)/sr)/2.0,1)
out*=(fi*fo)[:,None];out/=np.max(np.abs(out))*1.1
w=wave.open(sys.argv[1],'w');w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes((out*32767).astype('<i2').tobytes())
