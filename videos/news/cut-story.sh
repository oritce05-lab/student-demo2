#!/bin/sh
# טיזר הכתבה – עריכה נקייה של הכתבה המקורית: בלי שכבות, בגודל המקורי, עם הקול המקורי.
# הקטעים נחתכים רק בהפסקות בדיבור (נמצאו לפי עוצמת השמע):
#   0–31.85      פתיחה: המגיש ויובל, עד "...גם לעולם השיפוצים"
#   43.75–140.1  יובל מדגים, דקלה (פעמיים), השכרה לפי יום, מבחן האדם מול המכונה והתוצאה, יו"ר התאחדות קבלני השיפוצים
#   170.1–225    יו"ר ההתאחדות (המשך), והסיום "...ואת העבודה הקשה ישאיר לעובד החדש"
# הושמטו: רובוטי הקפה והחלונות (31.85–43.75) וסקירת הרובוטים הכללית (140.1–170.1).
# שימוש: sh cut-story.sh <source.mp4>
SRC="$1"; X=0.35
A=31.85; B0=43.75; B1=140.1; C0=170.1; C1=225.0
LA=$A; LB=$(echo "$B1-$B0" | bc); LC=$(echo "$C1-$C0" | bc)
O1=$(echo "$LA-$X" | bc); O2=$(echo "$LA+$LB-2*$X" | bc); END=$(echo "$LA+$LB+$LC-2*$X" | bc)
FV=$(echo "$END-1.1" | bc); FA=$(echo "$LC-1.2" | bc)
ffmpeg -y -v error -i "$SRC" -filter_complex "
[0:v]trim=0:$A,setpts=PTS-STARTPTS,fps=25[v0];[0:a]atrim=0:$A,asetpts=PTS-STARTPTS[a0];
[0:v]trim=$B0:$B1,setpts=PTS-STARTPTS,fps=25[v1];[0:a]atrim=$B0:$B1,asetpts=PTS-STARTPTS[a1];
[0:v]trim=$C0:$C1,setpts=PTS-STARTPTS,fps=25[v2];[0:a]atrim=$C0:$C1,asetpts=PTS-STARTPTS,afade=t=out:st=$FA:d=1.2[a2];
[v0][v1]xfade=transition=fade:duration=$X:offset=$O1[v01];[v01][v2]xfade=transition=fade:duration=$X:offset=$O2,fade=t=out:st=$FV:d=1.0[v];
[a0][a1]acrossfade=d=$X[a01];[a01][a2]acrossfade=d=$X[a]" -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart output/teaser-story-original.mp4
