package com.securemed.app.security

import android.os.SystemClock
import com.securemed.app.data.local.SecurePreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Idle lock for a signed-in session.
 *
 * A phone left on a ward desk is the threat this exists for: the session is
 * live, the chart is on screen, and nothing about the device's own lock screen
 * helps if the owner left it unlocked. After [SecurePreferences.idleTimeoutMinutes]
 * without interaction the app covers itself and asks for the fingerprint or the
 * device PIN before showing anything again.
 *
 * It replaces a `Handler.postDelayed` timeout that could not do the job:
 *
 *  - the callback was removed in `onPause`, so backgrounding the app *cancelled*
 *    the timeout instead of continuing it — a session left in the background all
 *    night came back untouched, with a full five minutes granted afresh;
 *  - `postDelayed` runs on `uptimeMillis`, which does not advance while the
 *    device is in deep sleep, so even had the callback survived it would not have
 *    fired on a phone that had been asleep in a pocket;
 *  - the timeout signed the user out rather than locking, discarding whatever
 *    they were in the middle of writing.
 *
 * Locking is a UI gate, not a cryptographic one: the tokens stay in
 * [SecurePreferences] (already AES-256-GCM at rest) and the composition stays
 * alive underneath, which is what lets an unlock return the user to the exact
 * screen — and the exact half-typed note — they left.
 */
object AppLock {

    /** Offered in settings. Deliberately no "off": this is a chart, not a game. */
    val TIMEOUT_CHOICES_MINUTES = listOf(1, 5, 15, 30)

    /**
     * How often a fresh mark is written while the user keeps interacting.
     *
     * Every touch would mean an AES round trip through
     * EncryptedSharedPreferences on the main thread. Throttling can only make
     * the recorded mark *older* than the real interaction, so the error is
     * always in the direction of locking sooner.
     */
    private const val MARK_INTERVAL_MS = 15_000L

    private val _locked = MutableStateFlow(false)

    /** True while the lock screen must cover the app. */
    val locked: StateFlow<Boolean> = _locked.asStateFlow()

    private val _timeoutMinutes = MutableStateFlow(5)

    /** Current idle timeout, so settings can render it without polling prefs. */
    val timeoutMinutes: StateFlow<Int> = _timeoutMinutes.asStateFlow()

    /** elapsedRealtime of the last mark actually written, for the throttle. */
    @Volatile
    private var lastWriteElapsed = 0L

    /** Called once from `SecureMedApp.onCreate()`. */
    fun init() {
        _timeoutMinutes.value = SecurePreferences.idleTimeoutMinutes
    }

    fun setTimeoutMinutes(minutes: Int) {
        if (minutes <= 0) return
        SecurePreferences.idleTimeoutMinutes = minutes
        _timeoutMinutes.value = minutes
        // A shorter timeout applies to the idle time already accumulated, so the
        // change can lock the app on the spot — which is the honest reading of
        // "lock after one minute" when the app has sat untouched for ten.
        lockIfIdle()
    }

    /**
     * Records "the user is here". Throttled; [force] writes regardless and is
     * used at the two moments the mark must be exact — unlocking, and the start
     * of a session.
     */
    fun noteInteraction(force: Boolean = false) {
        // While locked nothing counts as the user being present: taps land on the
        // lock overlay, and `onPause` reports the app leaving the foreground long
        // after it was covered. Refreshing the mark from either would hand out
        // unlocked time to whoever is holding the phone. [unlock] clears the flag
        // before it marks, so the one legitimate refresh still gets through.
        if (_locked.value) return
        val elapsed = SystemClock.elapsedRealtime()
        if (!force && lastWriteElapsed != 0L && elapsed - lastWriteElapsed < MARK_INTERVAL_MS) {
            return
        }
        lastWriteElapsed = elapsed
        SecurePreferences.recordLastSeen(elapsed, System.currentTimeMillis())
    }

    /**
     * Locks the app when the session has been idle past its timeout. Called on
     * every resume and by a foreground watchdog; returns the new lock state.
     */
    fun lockIfIdle(): Boolean {
        if (_locked.value) return true
        // Nothing to protect: no session, and no marks either (they are dropped
        // with the session), so the fail-closed branch below must not run here.
        if (!SecurePreferences.isLoggedIn()) return false

        val timeoutMs = _timeoutMinutes.value * 60_000L
        if (idleMillis() >= timeoutMs) {
            lock()
        }
        return _locked.value
    }

    fun lock() {
        _locked.value = true
        // The lock has to survive the process, not just the composition. Swiping
        // the app off the recents list kills it; without this the next launch
        // would find a recent mark, judge the session freshly used and open the
        // chart with no prompt at all — the lock defeated by the one gesture
        // anybody holding the phone would try. Removing the marks leaves the next
        // launch unable to say how long it has been idle, and [idleMillisFrom]
        // reads that as expired.
        lastWriteElapsed = 0L
        SecurePreferences.clearLastSeen()
    }

    /**
     * Called after a successful unlock, and after a successful login. Resets the
     * clock so the next idle period is measured from now.
     */
    fun unlock() {
        // Order matters: [noteInteraction] refuses to write while locked.
        _locked.value = false
        noteInteraction(force = true)
    }

    /**
     * Logout: nothing is left to lock, and the marks go with the session.
     *
     * A mark is written all the same, and it is not decoration. Signing out clears
     * the tokens over the network — `AuthViewModel.logout` returns immediately and
     * the wipe lands in a coroutine — so for as long as that request is in flight
     * [SecurePreferences.isLoggedIn] still answers true. If this logout followed a
     * lock, [lock] has already removed the marks, and the watchdog's next tick
     * would read "idle for an unknown time" against a session that still looks
     * live: the lock screen would come back over the login form the user was just
     * sent to. The user is demonstrably present — they pressed the button — so the
     * honest mark is now.
     */
    fun reset() {
        _locked.value = false
        noteInteraction(force = true)
    }

    private fun idleMillis(): Long = idleMillisFrom(
        elapsedMark = SecurePreferences.lastSeenElapsed,
        wallMark = SecurePreferences.lastSeenWall,
        nowElapsed = SystemClock.elapsedRealtime(),
        nowWall = System.currentTimeMillis()
    )
}

/**
 * How long the session has been untouched, according to whichever clock says the
 * longest — and [Long.MAX_VALUE] when neither can say anything.
 *
 * Each clock fails in a different direction, and taking the maximum means a
 * clock can only ever *shorten* the unlocked period:
 *
 *  - `elapsedRealtime` keeps counting through deep sleep and cannot be set, but
 *    restarts at zero on boot. After a reboot its delta is negative — the mark
 *    is larger than "now" — and is discarded as unusable.
 *  - the wall clock survives a reboot but the user can move it. Moved forward it
 *    locks the app early; moved backward it produces a negative delta, which is
 *    likewise discarded. Neither direction can buy extra unlocked time.
 *
 * With both unusable — a reboot plus a rolled-back clock, or marks that vanished
 * while the tokens survived — the honest answer is "unknown", and the safe
 * reading of unknown is expired. The cost of being wrong that way is one
 * fingerprint prompt; the cost of the opposite is a patient's chart open on a
 * phone somebody else is holding.
 *
 * Kept free of Android types so the arithmetic is unit-testable on the JVM.
 */
internal fun idleMillisFrom(
    elapsedMark: Long?,
    wallMark: Long?,
    nowElapsed: Long,
    nowWall: Long
): Long {
    val elapsedDelta = elapsedMark?.let { nowElapsed - it }?.takeIf { it >= 0L }
    val wallDelta = wallMark?.let { nowWall - it }?.takeIf { it >= 0L }
    return listOfNotNull(elapsedDelta, wallDelta).maxOrNull() ?: Long.MAX_VALUE
}
