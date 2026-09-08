package com.securemed.app.data.local

import com.securemed.app.data.model.Medication

/**
 * Local drug-interaction screen for the medication plans on this device.
 *
 * The dataset is a compact, well-known subset of the interactions a
 * general-practice prescriber meets most — the dangerous pairs (warfarin
 * bleeding risk, SSRI+tramadol serotonin syndrome, …) rather than a full
 * compendium. The check runs *on-device and offline* on purpose: it guards
 * the local plans the clinician builds in the app, where no server round
 * trip exists, and its verdict must not depend on connectivity.
 *
 * The names match on word boundaries and case-insensitively; matching on
 * substring alone would flag " aspirin" inside "rasagiline" (an MAOI) and
 * report an interaction that does not exist.
 */
object DrugInteractionChecker {

    /** One known interaction between two drug name patterns. */
    private data class Rule(
        val a: String,
        val b: String,
        val severity: Severity,
        val effect: String,
        val advice: String,
    )

    enum class Severity(val label: String) {
        MAJOR("خطير"),
        MODERATE("متوسط"),
        MINOR("بسيط"),
    }

    /** A fired rule against two concrete plan names. */
    data class Finding(
        val drugA: String,
        val drugB: String,
        val severity: Severity,
        val effect: String,
        val advice: String,
    )

    private val rules = listOf(
        Rule(
            "warfarin", "aspirin", Severity.MAJOR,
            "يزيد خطر النزف بشكل كبير",
            "تجنّب الجمع إلا بإشراف طبي مع مراقبة INR",
        ),
        Rule(
            "warfarin", "ibuprofen", Severity.MAJOR,
            "مضاد الالتهاب غير الستيرويدي يزيد خطر النزف المعوي",
            "يفضّل الباراسيتامول كمسكّن بديل",
        ),
        Rule(
            "warfarin", "paracetamol", Severity.MINOR,
            "الجرعات العالية المتكررة قد ترفع تأثير الوارفارين",
            "راقب INR عند الاستخدام المطوّل",
        ),
        Rule(
            "tramadol", "sertraline", Severity.MAJOR,
            "خطر متلازمة السيروتونين",
            "راقب الارتباك وتسرّع القلب وارتفاع الحرارة",
        ),
        Rule(
            "tramadol", "fluoxetine", Severity.MAJOR,
            "خطر متلازمة السيروتونين",
            "راقب الارتباك وتسرّع القلب وارتفاع الحرارة",
        ),
        Rule(
            "tramadol", "escitalopram", Severity.MAJOR,
            "خطر متلازمة السيروتونين",
            "راقب الارتباك وتسرّع القلب وارتفاع الحرارة",
        ),
        Rule(
            "tramadol", "moclobemide", Severity.MAJOR,
            "مثبط MAO مع ترامادول: ارتفاع ضغط خطير وتشنجات",
            "ممنوع الجمع؛ يجب فاصل زمني بينهما",
        ),
        Rule(
            "metformin", "contrast", Severity.MAJOR,
            "صبغة التباين قد تسبب حماض لبنيّ مع الميتفورمين",
            "أوقف الميتفورمين يوم الصبغة و48 ساعة بعدها وراقب الكرياتينين",
        ),
        Rule(
            "lisinopril", "spironolactone", Severity.MAJOR,
            "خطر ارتفاع البوتاسيوم المهدد للقلب",
            "راقب البوتاسيوم والكرياتينين دورياً",
        ),
        Rule(
            "lisinopril", "potassium", Severity.MODERATE,
            "مكمّلات البوتاسيوم ترفع الخطر مع مثبطات ACE",
            "راقب مستوى البوتاسيوم",
        ),
        Rule(
            "clopidogrel", "omeprazole", Severity.MODERATE,
            "الأوميبرازول يقلّل فعالية الكلوبيدوغريل عبر CYP2C19",
            "يفضّل البانتوبرازول عند الحاجة لمثبط مضخة البروتون",
        ),
        Rule(
            "simvastatin", "clarithromycin", Severity.MAJOR,
            "ارتفاع شديد في مستوى الستاتين: خطر تكسّر العضلات والفشل الكلوي",
            "أوقف الستاتين طوال فترة المضاد الحيوي",
        ),
        Rule(
            "simvastatin", "grapefruit", Severity.MODERATE,
            "الجريب فروت يثبط استقلاب الستاتين",
            "تجنّب الجريب فروت وعصيره",
        ),
        Rule(
            "digoxin", "amiodarone", Severity.MAJOR,
            "الأميودارون يرفع تركيز الديجوكسين بشدة",
            "خفّض جرعة الديجوكسين وراقب المستوى والتخطيط",
        ),
        Rule(
            "metformin", "alcohol", Severity.MODERATE,
            "الكحول يزيد خطر الحماض اللبنيّ مع الميتفورمين",
            "تجنّب الكحول أثناء العلاج",
        ),
        Rule(
            "ibuprofen", "lisinopril", Severity.MODERATE,
            "مضاد الالتهاب يضعف تأثير خافض الضغط ويضر الكلى",
            "يفضّل الباراسيتامول؛ راقب الضغط والكرياتينين",
        ),
        Rule(
            "amoxicillin", "methotrexate", Severity.MODERATE,
            "يرفع تركيز الميثوتريكسات: خطر سميّة",
            "راقب تعداد الدم ووظائف الكبد",
        ),
        Rule(
            "ciprofloxacin", "tizanidine", Severity.MAJOR,
            "يرفع تركيز التيزانيدين بشدة: هبوط ضغط وتثبيط تنفسي",
            "ممنوع الجمع",
        ),
        Rule(
            "codeine", "fluoxetine", Severity.MAJOR,
            "تحويل السيتوكروم قد يجعل الكوديين بلا فعالية مسكّنة",
            "أعد تقييم التسكين؛ قد يلزم أفيون آخر",
        ),
    )

    /**
     * Screens the active plans for a single patient against each other.
     *
     * The caller decides the population: one patient's list by default,
     * because cross-patient combinations are never consumed together.
     */
    fun checkPlans(plans: List<Medication>): List<Finding> {
        val findings = mutableListOf<Finding>()
        val active = plans.filter { it.isActive }

        for (i in active.indices) {
            for (j in i + 1 until active.size) {
                val rule = match(active[i], active[j])
                if (rule != null) {
                    findings += Finding(
                        drugA = active[i].name,
                        drugB = active[j].name,
                        severity = rule.severity,
                        effect = rule.effect,
                        advice = rule.advice,
                    )
                }
            }
        }
        return findings
    }

    /** Word-boundary, case-insensitive containment. */
    private fun mentions(planName: String, pattern: String): Boolean {
        val needle = Regex.escape(pattern)
        val boundary = Regex("(?i)(?<![\\p{L}])$needle(?![\\p{L}])")
        return boundary.containsMatchIn(planName)
    }

    private fun match(first: Medication, second: Medication): Rule? =
        rules.firstOrNull { r ->
            (mentions(first.name, r.a) && mentions(second.name, r.b)) ||
                (mentions(first.name, r.b) && mentions(second.name, r.a))
        }
}
