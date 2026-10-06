import parselmouth, sys, numpy as np
from parselmouth.praat import call
s=parselmouth.Sound(sys.argv[1])
p=s.to_pitch(); f0=p.selected_array['frequency']; f0=f0[f0>0]
print('orig median F0 %.0f Hz'%np.median(f0))
fr=float(sys.argv[3]); target=float(sys.argv[4])
m=call(s,"Change gender",75,600,fr,target,1.0,1.0)
p2=m.to_pitch(); g=p2.selected_array['frequency']; g=g[g>0]; print('new median F0 %.0f Hz'%np.median(g))
m.save(sys.argv[2],"WAV")
