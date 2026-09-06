package com.securemed.app.security

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit tests for [SecurityUtils] root detection.
 *
 * These used to drive `Build.TAGS` through `mockkStatic(Build::class)`. That can
 * never work: `TAGS` is a static *field*, and MockK intercepts static methods
 * only — both tests failed with MockKException before reaching the code under
 * test. The tags check now takes its input as a parameter, so it is tested as
 * the pure string check it always was.
 */
class SecurityUtilsTest {

    @Test
    fun `hasTestKeys is true when the build signature contains test-keys`() {
        assertTrue(SecurityUtils.hasTestKeys("release-keys,test-keys"))
        assertTrue(SecurityUtils.hasTestKeys("test-keys"))
    }

    @Test
    fun `hasTestKeys is false for a production signature`() {
        assertFalse(SecurityUtils.hasTestKeys("release-keys"))
    }

    /**
     * `Build.TAGS` is null off-device, so an absent signature must not read as
     * rooted — otherwise the release build's root gate would trip on any
     * device that reports no tags at all.
     */
    @Test
    fun `hasTestKeys is false when the build reports no tags`() {
        assertFalse(SecurityUtils.hasTestKeys(null))
        assertFalse(SecurityUtils.hasTestKeys(""))
    }

    /**
     * A JVM test host carries none of the su binaries the file check looks for
     * and no `which`, so the whole gate must come out false here. This is what
     * keeps the release-only check in MainActivity from being a self-inflicted
     * outage.
     */
    @Test
    fun `isDeviceRooted is false on a plain JVM host`() {
        assertFalse(SecurityUtils.isDeviceRooted())
    }
}
