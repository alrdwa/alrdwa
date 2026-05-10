# تشغيل عملي من جهازك: نظام توليد ونشر منشورات فيسبوك تلقائيًا (Ubuntu + n8n)

هذا الدليل نسخة **عملية تنفيذية**: تمشي معه خطوة بخطوة على جهازك، ومن النهاية تخرج بمنظومة تعمل فعليًا:

- توليد منشور تلقائي من فكرة.
- جدولة يومية.
- نشر تلقائي على Facebook Page.
- متابعة التفاعل وتحسين المحتوى.

> مهم: الأتمتة الرسمية تكون على **Facebook Pages** عبر Graph API، وليس الحساب الشخصي.

---

## 0) قبل البدء (Checklist سريع)

- جهاز Ubuntu متصل بالإنترنت.
- حساب فيسبوك فيه صفحة (Page) أنت Admin عليها.
- حساب Google (لو ستستخدم Google Sheets).
- مفتاح API لمزود ذكاء اصطناعي (مثل OpenAI).
- 60–90 دقيقة للإعداد أول مرة.

---

## 1) تثبيت الأدوات على Ubuntu (نفّذ كما هي)

```bash
sudo apt update
sudo apt install -y curl git jq ca-certificates
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g n8n
node -v
npm -v
n8n -v
```

تشغيل n8n:

```bash
n8n
```

افتح المتصفح على:
- `http://localhost:5678`

> اترك الطرفية مفتوحة أثناء العمل لأن n8n يعمل منها الآن.

---

## 2) إنشاء Facebook App + صلاحيات النشر

### 2.1 إنشاء التطبيق
1. افتح Meta for Developers.
2. Create App → نوع Business.
3. أضف Facebook Login + Pages API.

### 2.2 الصلاحيات الأساسية
- `pages_manage_posts`
- `pages_read_engagement`
- `pages_show_list`

### 2.3 الحصول على Page Access Token
1. أنشئ User Access Token بالصلاحيات أعلاه.
2. حوّله إلى long-lived token.
3. استخرج منه Page Access Token للصفحة التي ستنشر عليها.
4. احتفظ أيضًا بـ `page_id`.

---

## 3) إعداد مصدر الأفكار (Google Sheets)

أنشئ ملف Google Sheet باسم: `fb_content_queue`

ثم أضف الأعمدة التالية بالترتيب:

- `idea`
- `audience`
- `post_type`
- `publish_date`
- `publish_time`
- `status`
- `generated_caption`
- `hashtags`
- `fb_post_id`
- `engagement_score`
- `error_reason`

أدخل أول صف تجريبي مثلًا:
- idea: `3 أخطاء في التسويق بالمحتوى تمنع المبيعات`
- audience: `أصحاب المشاريع الصغيرة`
- post_type: `تعليمي`
- publish_date: تاريخ اليوم
- publish_time: بعد 20 دقيقة من الآن
- status: `draft`

---

## 4) إنشاء Workflow #1 (توليد المحتوى تلقائيًا)

داخل n8n:

1. **New Workflow** باسم: `FB - Generate Content`
2. أضف **Cron Node**:
   - Mode: Every Day
   - Time: 09:00
3. أضف **Google Sheets Node (Read Rows)**:
   - اختَر ملف `fb_content_queue`
   - فلتر `status = draft`
4. أضف **LLM Node / HTTP Request** لمزود الذكاء الاصطناعي.
5. استخدم هذا الـPrompt:

```text
أنت خبير صناعة محتوى عربي لفيسبوك.
أعد JSON فقط بالمفاتيح:
hook, caption_medium, cta, hashtags

الفكرة: {{ $json.idea }}
الجمهور: {{ $json.audience }}
نوع المنشور: {{ $json.post_type }}

شروط:
- بداية قوية في سطر أول.
- لغة عربية بسيطة.
- CTA مباشر.
- 5 إلى 8 هاشتاجات.
```

6. أضف **Set Node** لبناء النص النهائي:
   - `generated_caption = hook + "\n\n" + caption_medium + "\n\n" + cta`
   - `hashtags = join(hashtags, " ")`
   - `status = scheduled`
7. أضف **Google Sheets Node (Update Row)** لتحديث نفس السطر.
8. **Execute Workflow مرة واحدة يدويًا** للتجربة.

النتيجة المتوقعة:
- الصف يتحول من `draft` إلى `scheduled` ويحتوي caption جاهز.

---

## 5) إنشاء Workflow #2 (النشر المجدول على فيسبوك)

1. Workflow جديد باسم: `FB - Scheduled Publisher`
2. أضف **Cron Node** كل 15 دقيقة.
3. أضف **Google Sheets Read Rows** بشرط:
   - `status = scheduled`
   - `publish_date + publish_time <= now`
4. أضف **HTTP Request Node** (Facebook Graph API):
   - Method: `POST`
   - URL: `https://graph.facebook.com/v23.0/{{$json.page_id}}/feed`
   - Query/Auth:
     - `access_token = FB_PAGE_ACCESS_TOKEN`
   - Body (form-data أو x-www-form-urlencoded):
     - `message = {{$json.generated_caption + "\n\n" + $json.hashtags}}`
5. أضف **IF Node**:
   - إذا الاستجابة فيها `id` => نجاح.
6. نجاح:
   - Update Row:
     - `status = posted`
     - `fb_post_id = id`
7. فشل:
   - Update Row:
     - `status = failed`
     - `error_reason = رسالة الخطأ`

> في البداية جرّب على صف واحد فقط.

---

## 6) اختبار فعلي الآن (End-to-End)

نفّذ الترتيب التالي:

1. ضع صف `draft` في الشيت.
2. شغّل `FB - Generate Content` يدويًا.
3. تأكد أن الصف صار `scheduled`.
4. غيّر `publish_time` ليكون الآن أو قبل دقيقة.
5. شغّل `FB - Scheduled Publisher` يدويًا.
6. افتح صفحتك على فيسبوك وتأكد أن المنشور نزل.
7. تأكد في الشيت أن `status=posted` و `fb_post_id` موجود.

إذا هذا نجح → النظام أصبح يعمل.

---

## 7) إنشاء Workflow #3 (تجميع التفاعل يوميًا)

1. Workflow جديد: `FB - Analytics`
2. Cron يومي 10:00 مساءً.
3. اقرأ الصفوف التي `status=posted` خلال آخر 7 أيام.
4. لكل `fb_post_id` استدعِ Graph API لجلب:
   - reactions
   - comments
   - shares
5. احسب:

```text
engagement_score = reactions + comments*3 + shares*4
```

6. Update Row بقيمة `engagement_score`.
7. (اختياري) أرسل تقرير Telegram يومي بأفضل 3 منشورات.

---

## 8) إعداد متغيرات البيئة (مستحسن)

بدل كتابة الأسرار داخل كل Node، ضعها كمتغيرات بيئة.

```bash
export N8N_PORT=5678
export OPENAI_API_KEY="..."
export FB_PAGE_ACCESS_TOKEN="..."
export FB_PAGE_ID="..."
export CONTENT_SHEET_ID="..."
```

بعدها شغّل n8n من نفس الجلسة:

```bash
n8n
```

---

## 9) كيف ترفع التفاعل بشكل ملحوظ (عملي)

استخدم قاعدة أسبوعية بسيطة:

- 5 منشورات/أسبوع.
- 3 تعليمي + 1 قصة + 1 عرض.
- أول سطر دائمًا Hook قوي.
- CTA واحد فقط لكل منشور.
- راقب السكور أسبوعيًا واحذف الأنماط الضعيفة.

أمثلة CTA قوية:
- "اكتب (قالب) وسأرسل لك النموذج كاملًا."
- "أي نقطة تريدها كشرح فيديو؟"

---

## 10) حل المشاكل الشائعة بسرعة

- **401/403 من Facebook API**:
  - التوكن منتهي أو الصلاحيات ناقصة.
- **المنشور لا ينزل رغم success**:
  - تأكد أنك تنشر على `page_id` الصحيح.
- **الجدولة لا تعمل**:
  - راجع timezone في n8n + صيغة الوقت في الشيت.
- **النص العربي يخرج ركيك**:
  - حسّن الـPrompt وحدد اللهجة/الجمهور بدقة.

---

## 11) خطة تشغيل يومية (Ready-to-run)

- 09:00 صباحًا: توليد محتوى اليوم تلقائيًا.
- 01:00 ظهرًا: نشر المنشور الأساسي.
- 07:00 مساءً: منشور تفاعلي قصير.
- 10:00 مساءً: تحديث السكور + تقرير الأداء.

---

## الخلاصة

بهذه الخطوات أنت لا تحتاج تدخل يدوي إلا في المتابعة والتحسين. النظام سيولّد، يجدول، ينشر، ويقيس النتائج تلقائيًا من جهازك. ابدأ بنطاق صغير (صفحة واحدة + منشور يومي) ثم وسّع تدريجيًا.
