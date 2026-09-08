package com.securemed.app.security

import android.content.Context
import java.io.File

/**
 * Runtime instrumentation detection.
 *
 * The root check in [SecurityUtils] covers *static* markers of a modified
 * system image. This class covers the tools that actually sit between the app
 * and the OS at runtime and are what a real attacker uses against a health
 * records app:
 *
 *  * **Frida** — the de-facto standard for hooking JVM/Native code live.
 *    Detectable through its default server port, its injected agent library,
 *    and its gadget config files.
 *  * **Xposed/LSPosed** — framework modules that rewrite app behaviour at
 *    class-load time. Detectable through the loader classes they install and
 *    the files they ship.
 *  * **debugger/ptrace attachment** — a debugger attached to the process is
 *    either a developer (fine in a debug build) or someone trying to read
 *    PHI out of memory (not fine in release).
 *
 * Every check is heuristic on purpose: no single marker is proof, so the
 * caller receives a list of *signals* and decides what to do with them.
 * A debug build is exempt from enforcement by the caller (MainActivity),
 * because attaching a debugger to a debug build is the ordinary developer
 * workflow — flagging it would just train the team to ignore the warnings.
 */
object TamperDetection {

    /** One detected signal: which check fired and the evidence string. */
    data class Signal(
        val check: String,
        val evidence: String,
    )

    /** Default Frida server ports (27042 tcp, 27043 tls). */
    private val FRIDA_PORTS = listOf(27042, 27043)

    /** Paths that only exist when an injection framework is loaded. */
    private val SUSPICIOUS_FILES = listOf(
        // Frida gadget / agent, when injected the library name is randomized
        // but lives in the app's own lib dir with a recognizable prefix.
        "/data/local/tmp/re.frida.server",
        "/data/local/tmp/frida-server",
        // Xposed artefacts
        "/system/lib/libxposed_art.so",
        "/system/framework/XposedBridge.jar",
        "/system/bin/xposed",
    )

    /**
     * Collect tamper signals. Never throws: a detector that can crash the
     * app is a denial-of-service primitive against the very users it was
     * written to protect.
     */
    fun scan(context: Context): List<Signal> {
        val signals = mutableListOf<Signal>()

        runCatching { signals += fridaSignals() }
        runCatching { signals += xposedSignals() }
        runCatching { signals += fileSignals() }
        runCatching { signals += debuggerSignals() }
        runCatching { signals += emulatorSignals() }

        return signals
    }

    /** True when any signal fired — convenience for the enforcement call site. */
    fun isTamperingDetected(context: Context): Boolean = scan(context).isNotEmpty()

    private fun fridaSignals(): List<Signal> {
        val out = mutableListOf<Signal>()

        // The injected agent maps a page whose name starts with "frida".
        // /proc/self/maps is world-readable for one's own process and is the
        // cheapest reliable check that does not require root.
        runCatching {
            val maps = File("/proc/self/maps").readText()
            if (maps.contains("frida", ignoreCase = true)) {
                out += Signal("frida_maps", "frida agent mapped in process memory")
            }
        }

        // Default ports. Binding fails when nothing listens, so a successful
        // connect on a Frida port is a strong signal.
        for (port in FRIDA_PORTS) {
            runCatching {
                java.net.Socket().use { s ->
                    s.connect(java.net.InetSocketAddress("127.0.0.1", port), 200)
                }
                out += Signal("frida_port", "service answering on frida port $port")
            }
        }

        // Well-known environment variables the gadget honours.
        for (env in listOf("FRIDA_GADGET", "XZ_ENVIRONMENT")) {
            if (System.getenv(env) != null) {
                out += Signal("frida_env", "$env is set")
            }
        }
        return out
    }

    private fun xposedSignals(): List<Signal> {
        val out = mutableListOf<Signal>()
        val loaders = listOf(
            "de.robv.android.xposed.XposedBridge",
            "de.robv.android.xposed.XposedHelpers",
            "org.lsposed.lspd.core.Main",
        )
        for (name in loaders) {
            runCatching {
                Class.forName(name)
                out += Signal("xposed_loader", "$name loadable")
            }
        }
        return out
    }

    private fun fileSignals(): List<Signal> =
        SUSPICIOUS_FILES.filter { File(it).exists() }
            .map { Signal("suspicious_file", it) }

    /**
     * A tracing flag on our own process: JDWP is only ever attached by a
     * debugger or a tracing tool. In a debug build this is expected and the
     * caller does not enforce on it anyway.
     */
    private fun debuggerSignals(): List<Signal> {
        val out = mutableListOf<Signal>()
        runCatching {
            val status = File("/proc/self/status").readText()
            val tracer = Regex("""TracerPid:\s*(\d+)""")
                .find(status)?.groupValues?.get(1)?.toIntOrNull() ?: 0
            if (tracer != 0) {
                out += Signal("debugger", "TracerPid=$tracer")
            }
        }
        return out
    }

    private fun emulatorSignals(): List<Signal> {
        val out = mutableListOf<Signal>()
        if (SecurityUtils.isProbablyEmulator()) {
            out += Signal("emulator", SecurityUtils::class.simpleName ?: "emulator heuristic matched")
        }
        return out
    }
}
