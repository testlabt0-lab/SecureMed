package com.securemed.app.ui

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.io.File

/**
 * Robust, dependency-free CrashActivity.
 * Runs in its own process (:crash) so that memory or injection corruption
 * in the main process does not impact this diagnostic screen.
 */
class CrashActivity : Activity() {

    companion object {
        const val EXTRA_CRASH_INFO = "extra_crash_info"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val report = intent.getStringExtra(EXTRA_CRASH_INFO) ?: "لا توجد تفاصيل متاحة عن الخطأ."

        val rootLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#F9FAFB"))
            val pad = dpToPx(16)
            setPadding(pad, pad, pad, pad)
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        }

        val titleView = TextView(this).apply {
            text = "⚠️ تنبيه: حدث خطأ أثناء تشغيل التطبيق"
            textSize = 19f
            setTypeface(null, Typeface.BOLD)
            setTextColor(Color.parseColor("#DC2626"))
            setPadding(0, 0, 0, dpToPx(8))
        }
        rootLayout.addView(titleView)

        val subtitleView = TextView(this).apply {
            text = "واجه التطبيق استثناءً غير متوقع عند الفتح. يمكنك نسخ تقرير الخطأ لمعرفة السبب أو مسح البيانات وإعادة التشغيل."
            textSize = 14f
            setTextColor(Color.parseColor("#374151"))
            setPadding(0, 0, 0, dpToPx(14))
        }
        rootLayout.addView(subtitleView)

        // Buttons container
        val buttonsScroll = HorizontalScrollView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = dpToPx(12) }
        }

        val buttonsLayout = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }

        val copyButton = Button(this).apply {
            text = "نسخ التقرير"
            setBackgroundColor(Color.parseColor("#2563EB"))
            setTextColor(Color.WHITE)
            setOnClickListener {
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                val clip = ClipData.newPlainText("SecureMed Crash Report", report)
                clipboard.setPrimaryClip(clip)
                Toast.makeText(this@CrashActivity, "تم نسخ تقرير الخطأ إلى الحافظة بنجاح", Toast.LENGTH_SHORT).show()
            }
        }
        buttonsLayout.addView(copyButton)

        val spacer1 = View(this).apply {
            layoutParams = LinearLayout.LayoutParams(dpToPx(8), 1)
        }
        buttonsLayout.addView(spacer1)

        val restartButton = Button(this).apply {
            text = "إعادة التشغيل"
            setBackgroundColor(Color.parseColor("#0D9488"))
            setTextColor(Color.WHITE)
            setOnClickListener {
                restartApp()
            }
        }
        buttonsLayout.addView(restartButton)

        val spacer2 = View(this).apply {
            layoutParams = LinearLayout.LayoutParams(dpToPx(8), 1)
        }
        buttonsLayout.addView(spacer2)

        val clearDataButton = Button(this).apply {
            text = "مسح البيانات والبدء مجدداً"
            setBackgroundColor(Color.parseColor("#4B5563"))
            setTextColor(Color.WHITE)
            setOnClickListener {
                clearAppData()
                restartApp()
            }
        }
        buttonsLayout.addView(clearDataButton)

        buttonsScroll.addView(buttonsLayout)
        rootLayout.addView(buttonsScroll)

        // Stack trace scroll area
        val logScrollView = ScrollView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1.0f
            )
            setBackgroundColor(Color.parseColor("#1F2937"))
            val innerPad = dpToPx(12)
            setPadding(innerPad, innerPad, innerPad, innerPad)
        }

        val logTextView = TextView(this).apply {
            text = report
            textSize = 12f
            setTextColor(Color.parseColor("#F3F4F6"))
            typeface = Typeface.MONOSPACE
            setTextIsSelectable(true)
        }
        logScrollView.addView(logTextView)
        rootLayout.addView(logScrollView)

        setContentView(rootLayout)
    }

    private fun restartApp() {
        val launchIntent = packageManager.getLaunchIntentForPackage(packageName)?.apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        }
        if (launchIntent != null) {
            startActivity(launchIntent)
        }
        finish()
        android.os.Process.killProcess(android.os.Process.myPid())
    }

    private fun clearAppData() {
        runCatching {
            // Delete databases
            val dbDir = File(applicationInfo.dataDir, "databases")
            if (dbDir.exists()) dbDir.deleteRecursively()

            // Delete shared_prefs
            val spDir = File(applicationInfo.dataDir, "shared_prefs")
            if (spDir.exists()) spDir.deleteRecursively()

            // Delete offline cache
            val cacheDir = File(filesDir, "offline_cache")
            if (cacheDir.exists()) cacheDir.deleteRecursively()
        }
        Toast.makeText(this, "تم تنظيف البيانات المحلية بنجاح", Toast.LENGTH_SHORT).show()
    }

    private fun dpToPx(dp: Int): Int {
        val density = resources.displayMetrics.density
        return (dp * density).toInt()
    }
}
