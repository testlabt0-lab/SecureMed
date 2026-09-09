package com.securemed.app.data.local.room

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The one lossy-looking field of the medication migration is `times` — a
 * list squeezed into a comma-joined column. These tests pin the round-trip
 * the JSON→Room migration relies on: whatever `LocalCache` held as
 * `["08:00","20:00"]` must come back as the same list after storage.
 */
class MedicationPlanEntityTest {

    @Test
    fun `join then split preserves dose times`() {
        val times = listOf("08:00", "20:00", "13:30")

        val joined = MedicationPlanEntity.joinTimes(times)
        val split = MedicationPlanEntity.splitTimes(joined)

        assertEquals(times, split)
    }

    @Test
    fun `split tolerates stray whitespace and empties`() {
        val split = MedicationPlanEntity.splitTimes(" 08:00 , , 20:00,")

        assertEquals(listOf("08:00", "20:00"), split)
    }

    @Test
    fun `empty times round-trip to empty list`() {
        assertTrue(MedicationPlanEntity.splitTimes(MedicationPlanEntity.joinTimes(emptyList())).isEmpty())
        assertTrue(MedicationPlanEntity.splitTimes("").isEmpty())
    }
}
