# Arabic Kinetic Typography — Abaya Video (Production v2)

مشروع إنتاج فيديو موشن جرافيك تايبوغرافي عربي عمودي وفق السيناريو المعتمد، باستخدام Remotion + React + TypeScript + CSS وPython + FFmpeg.

## المواصفات المعتمدة

- المقاس: 1080 × 1920 (عمودي 9:16).
- معدل الإطارات: 30 FPS.
- الطول: 670 إطاراً = 22.333 ثانية تقريباً (يعرض عادةً 22.3 ثانية).
- عدد المشاهد: 6.
- الخلفية: `#FADAD8`.
- النص الأساسي: `#171717`.
- لون التأكيد والملصقات: `#C94F76`.
- النص فوق العباءة: `#FFFFFF`.
- لا توجد علامة مائية أو اسم حساب.

## المصدر الصوتي المستخدم

لم يكن ملف الفيديو الأصلي متاحاً ضمن المرفقات التي وصلت إلى مساحة التنفيذ، لذلك اختير بديل Edge TTS الذي ورد ضمن خيارات الطلب. يقوم `scripts/generate_narration.py` بتوليد النص المحدد بصوت `ar-SA-HamedNeural`، ويستخرج أحداث `WordBoundary` من Edge TTS، ثم يبني `public/audio/narration.wav` بطول 670 إطاراً ويكتب توقيت كل كلمة في:

- `public/audio/narration-word-timings.json`
- `src/data/timeline.json` داخل `wordTimings`

يُقسّم التعليق إلى ست وحدات مرتبطة ببدايات المشاهد، مع الحفاظ على ترتيب النص الكامل. إذا تجاوز أي مقطع نافذته الزمنية، يضبط السكريبت سرعته بمقدار محسوب فقط حتى يلائم النافذة؛ وتُحوّل التوقيتات اللفظية بنفس عامل السرعة.

## الأصول المرئية

الصورة الرئيسية المعتمدة هي قصاصة PNG شفافة أمامية لعباءة سوداء. تُشتق منها الحالات الأربع في `scripts/create_abaya_variants.py` مع الحفاظ على الأبعاد والتمركز وحدود القصّة ذاتها:

1. `element-01.png`: سوداء سادة.
2. `element-02.png`: نقش أسود خفي على الأسود.
3. `element-03.png`: تطريز ذهبي ووردي ظاهر على الحواف والأكمام.
4. `element-04.png`: النسخة المطرزة شبه الشفافة.

توجد الصورة الرئيسية في `public/images/abaya-master.webp` لإعادة إنتاج الحالات عند الحاجة.

## الخطوط والمؤثرات

ينزّل GitHub Actions خطّي Noto Sans Arabic وNoto Naskh Arabic مباشرةً من مستودع Google Fonts ويحفظ ملفات الترخيص في `public/fonts/`. ويولّد `scripts/generate_sfx.py` مؤثري Pop وWhoosh بصيغة WAV، ثم يخلطهما `mix_audio.py` عند 20% من متوسط مستوى التعليق الصوتي (ضمن النطاق 15–25%).

## التشغيل المحلي

يتطلب Node.js 20+ وPython 3.12+ وFFmpeg وFFprobe واتصالاً بالإنترنت لتوليد Edge TTS وتنزيل الخطوط.

```bash
python -m pip install -r requirements.txt
npm install
python scripts/create_abaya_variants.py
python scripts/generate_narration.py
python scripts/generate_sfx.py
npm run check-timeline
npm run mix-audio
npm run render
npm run validate
```

## التشغيل السحابي

Workflow: `.github/workflows/render.yml` على الفرع `integrate/arabic-kinetic-video-v2`، ويقوم بتنزيل الخطوط، وتوليد الصوت والكلمات والمؤثرات، وفحص TypeScript، ثم التصيير والتحقق ورفع:

- `out/final-video.mp4`
- `out/render-validation.json`
- `out/audio-mix-report.json`
- `out/narration-report.json`
- `public/audio/narration-word-timings.json`

يُحفظ Artifact لمدة 14 يوماً.

## ملاحظة بشأن التطابق

الصوت في هذه النسخة هو تعليق اصطناعي عبر الصوت المطلوب `ar-SA-HamedNeural`، وليس استخراجاً من الفيديو الأصلي؛ لأن ملف ذلك الفيديو لم يصل إلى هذه المحادثة. لا تدّعي هذه النسخة مطابقة أداء تسجيل أصلي غير متاح.


## Timeline validation

The production example is checked in two layers:

- `scripts/validate_timeline_generic.py` checks the reusable timeline structure: project dimensions and duration, scene ordering and bounds, event ranges, palette references, and referenced public assets.
- `scripts/validate_timeline.py` remains the stricter abaya-example profile. It checks the approved six-scene transcript, timings, palette, image states, and narration requirements.

Run both with `npm run check-timeline`. The generic validator has unit tests covering valid alternate project dimensions, overlapping scenes, invalid event ranges, path traversal, and unknown palette tokens; run them with `npm test`.
