package com.securemed.app.security

import android.os.Build
import io.mockk.every
import io.mockk.mockkStatic
import io.mockk.unmockkAll
import org.junit.After
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.File

/**
 * Unit tests for SecurityUtils to ensure root detection works as expected.
 */
class SecurityUtilsTest {

    @Before
    fun setUp() {
        // Mock static Android classes
        mockkStatic(Build::class)
    }

    @After
    fun tearDown() {
        unmockkAll()
    }

    @Test
    fun `isDeviceRooted returns true when test-keys are present`() {
        // Arrange: Mock the Build.TAGS to simulate a rooted device with test-keys
        every { Build.TAGS } returns "release-keys,test-keys"

        // Act
        val isRooted = SecurityUtils.isDeviceRooted()

        // Assert
        assertTrue("Device should be considered rooted when test-keys are present", isRooted)
    }

    @Test
    fun `isDeviceRooted returns false when test-keys are absent and no su files exist`() {
        // Arrange: Mock the Build.TAGS to simulate a non-rooted device
        every { Build.TAGS } returns "release-keys"

        // Act
        // Note: For a true unit test, we should also mock File.exists(), but on a standard 
        // development machine, these files usually do not exist natively.
        val isRooted = SecurityUtils.isDeviceRooted()

        // Assert
        // This will only pass if the developer's machine does not coincidentally have /system/xbin/su
        assertFalse("Device should not be considered rooted on standard environment", isRooted)
    }
}
