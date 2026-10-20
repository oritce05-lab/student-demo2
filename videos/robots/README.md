# סרטון שיווקי – רובוטים בבנייה

סרטון 16:9 (1920×1080, 45 שניות) שנבנה מ-`scene.html` ומצולם פריים אחר פריים.

```bash
# 1. חילוץ קטעי הווידאו מהסרטון המקורי (לא נשמרים ב-git)
V=<path-to-source.mp4>
for s in "a 13.5 4.5" "b 23 6.5" "c 33.5 6" "d 51 5"; do set -- $s; mkdir -p assets/clips/$1
  ffmpeg -y -ss $2 -t $3 -i "$V" -vf "scale=-2:1000:flags=lanczos,unsharp=5:5:0.6,eq=contrast=1.06:saturation=1.12,fps=30" -q:v 3 assets/clips/$1/%04d.jpg; done
# 2. תצוגה מקדימה / הפקה
node render.mjs --preview
node render.mjs          # output/robots-construction.mp4
```
