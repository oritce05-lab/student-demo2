#!/bin/sh
# מוסיף לטיזר הכתבה את התגית "מדריך ראשי להכשרת מפעילי הרובוטיקה" מתחת לאיש העבודה המנוסה,
# בזמן שהצילום הרחב של שלושת המשתתפים על המסך. שאר הסרטון לא משתנה (הקול מועתק כמו שהוא).
IN=output/teaser-story-original.mp4; OUT=output/teaser-story-original-tag.mp4
X=117; Y=232; A1=74.85; B1=82.55; A2=85.85; B2=90.75; F=0.35
ffmpeg -y -v error -i "$IN" -loop 1 -i assets/tag.png -loop 1 -i assets/tag.png -filter_complex "
[1:v]scale=197:-1,format=rgba,trim=0:$(echo "$B1-$A1" | bc),setpts=PTS-STARTPTS+$A1/TB,fade=t=in:st=$A1:d=$F:alpha=1,fade=t=out:st=$(echo "$B1-$F" | bc):d=$F:alpha=1[t1];
[2:v]scale=197:-1,format=rgba,trim=0:$(echo "$B2-$A2" | bc),setpts=PTS-STARTPTS+$A2/TB,fade=t=in:st=$A2:d=$F:alpha=1,fade=t=out:st=$(echo "$B2-$F" | bc):d=$F:alpha=1[t2];
[0:v][t1]overlay=$X:$Y:eof_action=pass[v1];[v1][t2]overlay=$X:$Y:eof_action=pass[v]" -map "[v]" -map 0:a -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a copy -movflags +faststart "$OUT"
