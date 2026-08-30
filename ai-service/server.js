/**
 * SecureMed Smart Assistant Service
 * ----------------------------------
 * GLM-powered assistant (via z-ai-web-dev-sdk).
 *
 * Endpoints:
 *   POST /ask           { question, context?, history? }        → { answer }
 *   POST /case-summary  { patient, records, channels, meta? }   → { summary, generated_at }
 *   GET  /health                                                → { status }
 *
 * Runs on port 8100 (proxied by the Vite dev server at /ai).
 * The /case-summary endpoint is called server-side by Django
 * (backend/apps/patients/views.py → ai_summary action) AFTER it has
 * verified the requester's permissions — the AI never sees data the
 * requester is not allowed to view.
 */
import express from 'express';
import ZAI from 'z-ai-web-dev-sdk';

const app = express();
app.use(express.json({ limit: '1mb' }));

const PORT = process.env.PORT || 8100;

let zaiInstance = null;
async function getZAI() {
  if (!zaiInstance) zaiInstance = await ZAI.create();
  return zaiInstance;
}

const SYSTEM_PROMPT = `أنت «المساعد الذكي» في منصة SecureMed — منصة سحابية آمنة لإدارة الحالات الطبية (القنوات) والسجلات الصحية، مبنية على منهجية DevSecOps بأحدث معايير الأمان (OWASP Top 10، WAF، JWT، WebAuthn، تشفير AES-256).

مهمتك: مساعدة الكادر الطبي (أطباء، ممرضون، مدراء، مراجعون أمنيون) بالإجابة على أسئلتهم عن المنصة وبياناتها الحية المزوّدة لك في سياق الطلب.

قواعد صارمة:
1. أجب بالعربية فقط، بأسلوب مهني واضح ومختصر.
2. اعتمد حصراً على بيانات السياق المرفقة عند الإجابة عن الأرقام أو الإحصائيات — لا تخترع أرقاماً أبداً.
3. إذا لم تكن المعلومة موجودة في السياق، قل ذلك بصراحة واقترح على المستخدم فتح الصفحة المناسبة في المنصة.
4. لا تطلب ولا تعرض بيانات حساسة (كلمات مرور، مفاتيح، أسرار TOTP، بيانات بطاقات).
5. عند السؤال عن مفاهيم أمنية أو DevSecOps، اشرح بإيجاز مع ربطها بميزات المنصة.
6. يمكنك استخدام تنسيق Markdown بسيط (عناوين، قوائم، **غامق**).
7. اجعل الإجابة مركزة: من 2 إلى 8 أسطر كحد أقصى عدا طلب شرح مفصل.`;

app.get('/health', (_req, res) => {
  res.json({ status: 'healthy', service: 'SecureMed AI Assistant' });
});

// ============================================================
// Clinical case summary (called by Django backend, server-to-server)
// ============================================================
const CASE_SUMMARY_PROMPT = `أنت «ملخص الحالة الذكي» في منصة SecureMed الطبية الآمنة.

مهمتك: توليد ملخص سريري احترافي بالعربية عن حالة المريض، اعتماداً حصرياً على البيانات المرفقة في الطلب (بيانات المريض + السجلات الطبية + القنوات).

القواعد الصارمة:
1. اعتمد حصرياً على البيانات المرفقة — لا تخترع تشخيصاً أو دواءً أو قياساً غير موجود فيها إطلاقاً.
2. إن كانت البيانات قليلة، اذكر ذلك بصراحة وقدم ملخصاً موجزاً لما هو متوفر فقط.
3. ابدأ بعنوان «ملخص الحالة السريرية» ثم نظّم الملخص بالأقسام التالية عند توفر بياناتها:
   **نظرة عامة** (بيانات تعريفية مختصرة: العمر، الفئة الدموية، الحساسية إن وجدت)
   **أبرز النتائج والملاحظات السريرية** (من السجلات: تشخيصات، نتائج مختبر، مؤشرات حيوية)
   **الأدوية والوصفات** (إن وُجدت)
   **النقاط التي تستدعي الانتباه** (سجلات حرجة، حساسية، مؤشرات مرتفعة)
   **التوصيات المتاحة ضمن السجل** (إن وُجدت توصيات صريحة في السجلات فقط)
4. لا تقدّم تشخيصاً جديداً ولا توصية علاجية من عندك — أنت تلخّص السجل فقط.
5. أضف في النهاية سطراً: «هذا الملخص مولّد آلياً من سجلات المنصة ويُستخدم للمساعدة فقط ولا يُغني عن المراجعة الطبية البشرية.»
6. استخدم تنسيق Markdown (عناوين، قوائم، **غامق**). الطول: 120-300 كلمة حسب حجم البيانات.`;

app.post('/case-summary', async (req, res) => {
  try {
    const { patient, records, channels, meta } = req.body || {};
    if (!patient || !Array.isArray(records)) {
      return res.status(400).json({ error: 'بيانات المريض والسجلات مطلوبة' });
    }

    const payload = {
      patient: {
        full_name: patient.full_name,
        gender: patient.gender,
        age: patient.age,
        blood_type: patient.blood_type,
        allergies: patient.allergies,
        chronic_conditions: patient.chronic_conditions,
      },
      channels: (channels || []).slice(0, 10).map((c) => ({
        name: c.name, type: c.channel_type, priority: c.priority, status: c.status,
      })),
      records: records.slice(0, 40).map((r) => ({
        type: r.record_type,
        title: r.title,
        content: String(r.content || '').slice(0, 800),
        is_critical: r.is_critical,
        created_at: r.created_at,
      })),
      meta: meta || {},
    };

    const contextText =
      `\n\n=== بيانات الحالة (آخر تحديث ${new Date().toISOString()}) ===\n` +
      `${JSON.stringify(payload).slice(0, 14000)}\n=== نهاية البيانات ===`;

    const zai = await getZAI();
    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'assistant', content: CASE_SUMMARY_PROMPT + contextText },
        { role: 'user', content: 'ولّد ملخص الحالة السريرية لهذا المريض من البيانات المرفقة فقط.' },
      ],
      thinking: { type: 'disabled' },
    });

    const summary = completion?.choices?.[0]?.message?.content;
    if (!summary || !summary.trim()) {
      return res.status(502).json({ error: 'لم يصل رد من نموذج الذكاء الاصطناعي' });
    }
    res.json({ summary, generated_at: new Date().toISOString() });
  } catch (err) {
    console.error('[ai-service] case-summary error:', err.message);
    res.status(500).json({ error: 'خطأ في توليد ملخص الحالة، حاول مجدداً' });
  }
});

app.post('/ask', async (req, res) => {
  try {
    const { question, context, history } = req.body || {};
    if (!question || !String(question).trim()) {
      return res.status(400).json({ error: 'السؤال مطلوب' });
    }
    if (String(question).length > 2000) {
      return res.status(400).json({ error: 'السؤال طويل جداً' });
    }

    const contextText = context
      ? `\n\n=== بيانات المنصة الحية (آخر تحديث ${new Date().toISOString()}) ===\n${JSON.stringify(context).slice(0, 12000)}\n=== نهاية البيانات ===`
      : '';

    const messages = [{ role: 'assistant', content: SYSTEM_PROMPT + contextText }];

    // limited conversation memory (last 6 turns)
    if (Array.isArray(history)) {
      for (const h of history.slice(-6)) {
        if (h && (h.role === 'user' || h.role === 'assistant') && typeof h.content === 'string') {
          messages.push({ role: h.role, content: h.content.slice(0, 4000) });
        }
      }
    }
    messages.push({ role: 'user', content: String(question).trim() });

    const zai = await getZAI();
    const completion = await zai.chat.completions.create({
      messages,
      thinking: { type: 'disabled' },
    });

    const answer = completion?.choices?.[0]?.message?.content;
    if (!answer || !answer.trim()) {
      return res.status(502).json({ error: 'لم يصل رد من نموذج الذكاء الاصطناعي' });
    }
    res.json({ answer });
  } catch (err) {
    console.error('[ai-service] error:', err.message);
    res.status(500).json({ error: 'خطأ في خدمة المساعد الذكي، حاول مجدداً' });
  }
});

app.listen(PORT, () => {
  console.log(`[ai-service] SecureMed Smart Assistant listening on :${PORT}`);
});
