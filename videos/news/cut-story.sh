#!/bin/sh
# טיזר הכתבה – עריכה נקייה של הכתבה המקורית: בלי שכבות, בגודל המקורי, עם הקול המקורי.
# הקטעים נחתכים רק בהפסקות בדיבור (נמצאו לפי עוצמת השמע).
# שימוש: sh cut-story.sh <source.mp4>
SRC="$1"; X=0.35
ffmpeg -y -v error -i "$SRC" -filter_complex "
[0:v]trim=0:31.85,setpts=PTS-STARTPTS,fps=25[v0];[0:a]atrim=0:31.85,asetpts=PTS-STARTPTS[a0];
[0:v]trim=43.75:77.3,setpts=PTS-STARTPTS,fps=25[v1];[0:a]atrim=43.75:77.3,asetpts=PTS-STARTPTS[a1];
[0:v]trim=205.15:225.0,setpts=PTS-STARTPTS,fps=25[v2];[0:a]atrim=205.15:225.0,asetpts=PTS-STARTPTS,afade=t=out:st=18.6:d=1.2[a2];
[v0][v1]xfade=transition=fade:duration=$X:offset=31.5[v01];[v01][v2]xfade=transition=fade:duration=$X:offset=64.7,fade=t=out:st=83.4:d=1.0[v];
[a0][a1]acrossfade=d=$X[a01];[a01][a2]acrossfade=d=$X[a]" -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart output/teaser-story-original.mp4
