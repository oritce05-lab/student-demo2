import numpy as np,wave,sys,json
sr=44100;D=float(sys.argv[2]);marks=json.loads(sys.argv[3]) if len(sys.argv)>3 else []
N=int(sr*D);out=np.zeros((N,2));rng=np.random.default_rng(3)
note=lambda m:440*2**((m-69)/12)
def add(sig,st,pan=(1,1)):
    i=int(st*sr);n=min(len(sig),N-i)
    if n>0 and i>=0: out[i:i+n,0]+=sig[:n]*pan[0];out[i:i+n,1]+=sig[:n]*pan[1]
bpm=112;beat=60/bpm;bar=4*beat
prog=[[62,66,69],[59,62,66],[55,59,62],[57,61,64]]  # D Bm G A
u=lambda d:np.arange(int(d*sr))/sr
def kick():
    t=u(.3);f=45+110*np.exp(-t*35);return .55*np.exp(-t*10)*np.sin(2*np.pi*np.cumsum(f)/sr)
def clap():
    t=u(.18);n=rng.standard_normal(len(t));env=np.exp(-t*30)*(1+.6*np.exp(-((t-.012)*300)**2));return .16*env*np.diff(n,prepend=0)
def hat(a=.05):
    t=u(.05);return a*np.exp(-t*90)*np.diff(rng.standard_normal(len(t)),prepend=0)
def pluck(m,a=.07,d=.35):
    t=u(d);f=note(m);return a*np.exp(-t*9)*(np.sign(np.sin(2*np.pi*f*t))*.35+np.sin(2*np.pi*f*t))*np.minimum(t/.004,1)
k=0;t=0.0
while t<D:
    ch=prog[k%4]
    for b in range(4):
        st=t+b*beat
        if st>D-1.0: break
        add(kick(),st)
        if b in(1,3): add(clap(),st)
        add(hat(.035),st+beat/2,(0.8,1));add(hat(.02),st+beat/4,(1,.7));add(hat(.02),st+3*beat/4,(.7,1))
        # bass
        bt=u(beat*.9);fb=note(ch[0]-24);add(.16*np.exp(-bt*3)*np.tanh(2*np.sin(2*np.pi*fb*bt)),st)
    # plucky chord rhythm
    for i,pos in enumerate([0,.75,1.5,2.5,3,3.5]):
        for m in ch: add(pluck(m+12,.035),t+pos*beat,(1,.75) if i%2 else (.75,1))
    # top melody hook
    mel=[ch[2]+12,ch[1]+12,ch[0]+24,ch[1]+12]
    for i,m in enumerate(mel): add(pluck(m,.05,.3),t+(i*1+.5)*beat,(.85,1))
    t+=bar;k+=1
for mk in marks:  # whoosh + pop on scene changes
    t2=u(.45);n=np.convolve(rng.standard_normal(len(t2)),np.ones(10)/10,'same');add(.18*np.sin(np.pi*t2/.45)**2*n,mk-.3)
    add(.12*np.exp(-u(.12)*40)*np.sin(2*np.pi*(900-3000*u(.12))*u(.12)),mk)
fo=np.minimum((D-np.arange(N)/sr)/1.5,1);out*=fo[:,None];out/=np.max(np.abs(out))*1.15
w=wave.open(sys.argv[1],'w');w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes((out*32767).astype('<i2').tobytes())
