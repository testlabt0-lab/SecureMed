package com.securemed.app.security

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Unit tests for the idle arithmetic behind [AppLock].
 *
 * Only [idleMillisFrom] is covered, and that is why it exists as a top-level
 * function taking its clocks as parameters: `AppLock` itself reads
 * `SystemClock.elapsedRealtime()` and `EncryptedSharedPreferences`, neither of
 * which a plain JVM test host can provide, and this project has no Robolectric.
 *
 * The rule under test is fail-closed: idle time is whichever clock reports the
 * *longest* gap, an unusable clock is discarded rather than trusted, and with no
 * usable clock at all the session counts as expired.
 */
class AppLockTest {

    private val minute = 60_000L

    @Test
    fun `idle time is the longer of the two clocks`() {
        val idle = idleMillisFrom(
            elapsedMark = 1_000L,
            wallMark = 1_000L,
            nowElapsed = 1_000L + 2 * minute,
            nowWall = 1_000L + 7 * minute
        )
        assertEquals(7 * minute, idle)
    }

    /**
     * A device that rebooted while the session lived: `elapsedRealtime` restarted
     * at zero, so its mark is now larger than "now". The delta is negative and
     * must be discarded — not clamped to zero, which would read as "the user was
     * here a moment ago".
     */
    @Test
    fun `a reboot leaves the wall clock in charge`() {
        val idle = idleMillisFrom(
            elapsedMark = 9_000_000L,
            wallMark = 1_700_000_000_000L,
            nowElapsed = 12_000L,
            nowWall = 1_700_000_000_000L + 40 * minute
        )
        assertEquals(40 * minute, idle)
    }

    /**
     * The wall clock moved backwards — the one move that could buy unlocked time,
     * since a forward move only locks sooner. Its delta is negative, so
     * `elapsedRealtime` answers alone.
     */
    @Test
    fun `a rolled back wall clock cannot buy unlocked time`() {
        val idle = idleMillisFrom(
            elapsedMark = 5_000L,
            wallMark = 1_700_000_000_000L,
            nowElapsed = 5_000L + 20 * minute,
            nowWall = 1_700_000_000_000L - 3 * 60 * minute
        )
        assertEquals(20 * minute, idle)
    }

    /** A reboot *and* a rolled-back clock: nothing left to measure with. */
    @Test
    fun `two unusable clocks read as expired`() {
        val idle = idleMillisFrom(
            elapsedMark = 9_000_000L,
            wallMark = 1_700_000_000_000L,
            nowElapsed = 12_000L,
            nowWall = 1_700_000_000_000L - minute
        )
        assertEquals(Long.MAX_VALUE, idle)
    }

    /**
     * Marks that vanished while the tokens survived — a cleared prefs file, or a
     * session written by a build that predates the marks. Unknown must read as
     * expired: the cost is one unlock prompt, the alternative is an open chart.
     */
    @Test
    fun `absent marks read as expired`() {
        assertEquals(
            Long.MAX_VALUE,
            idleMillisFrom(elapsedMark = null, wallMark = null, nowElapsed = 5_000L, nowWall = 1_700_000_000_000L)
        )
    }

    /** One mark present is enough to measure with. */
    @Test
    fun `a single usable clock answers on its own`() {
        assertEquals(
            3 * minute,
            idleMillisFrom(
                elapsedMark = 1_000L,
                wallMark = null,
                nowElapsed = 1_000L + 3 * minute,
                nowWall = 1_700_000_000_000L
            )
        )
        assertEquals(
            3 * minute,
            idleMillisFrom(
                elapsedMark = null,
                wallMark = 1_700_000_000_000L,
                nowElapsed = 1_000L,
                nowWall = 1_700_000_000_000L + 3 * minute
            )
        )
    }

    /** Interaction a moment ago, on both clocks, is not idle time. */
    @Test
    fun `a fresh mark reports almost no idle time`() {
        val idle = idleMillisFrom(
            elapsedMark = 500_000L,
            wallMark = 1_700_000_000_000L,
            nowElapsed = 500_120L,
            nowWall = 1_700_000_000_120L
        )
        assertEquals(120L, idle)
    }

    /**
     * The timeout choices offered in settings. Guards the two properties the
     * lock depends on rather than the exact list: no value may disable the lock,
     * and the default of five minutes has to be one of them or the settings
     * screen would open with nothing selected.
     */
    @Test
    fun `every timeout choice is a positive number of minutes`() {
        assertEquals(emptyList<Int>(), AppLock.TIMEOUT_CHOICES_MINUTES.filter { it <= 0 })
        assertEquals(true, AppLock.TIMEOUT_CHOICES_MINUTES.contains(5))
    }
}
