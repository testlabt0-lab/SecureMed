"""
Unit tests for Dynamic Data Masking (DDM) and Upload Sanitization.
"""
from unittest import TestCase
from unittest.mock import MagicMock
from apps.core.masking import (
    mask_national_id,
    mask_phone,
    mask_name,
    mask_address,
    mask_patient_dict,
    should_unmask_patient,
)


class DynamicDataMaskingTests(TestCase):
    """Test masking functions across various PHI/PII data formats."""

    def test_mask_national_id(self):
        self.assertEqual(mask_national_id("1092837461"), "******7461")
        self.assertEqual(mask_national_id("1234"), "****")
        self.assertEqual(mask_national_id(""), "")
        self.assertEqual(mask_national_id(None), "")

    def test_mask_phone(self):
        # International Saudi number
        self.assertEqual(mask_phone("+966501234567"), "+9665*****567")
        # Local format
        self.assertEqual(mask_phone("0501234567"), "050****567")
        self.assertEqual(mask_phone(""), "")
        self.assertEqual(mask_phone(None), "")

    def test_mask_name(self):
        self.assertEqual(mask_name("أحمد محمد الشهري"), "أحمد م. ****")
        self.assertEqual(mask_name("سارة علي"), "سارة ع. ****")
        self.assertEqual(mask_name("John Doe"), "John D. ****")
        self.assertEqual(mask_name("أحمد"), "أحمد")
        self.assertEqual(mask_name(""), "")
        self.assertEqual(mask_name(None), "")

    def test_mask_address(self):
        self.assertEqual(mask_address("الرياض - حي الصحافة - شارع العليا"), "الرياض - [عنوان محمي]")
        self.assertEqual(mask_address("جدة، حي الروضة"), "جدة - [عنوان محمي]")
        self.assertEqual(mask_address("عنوان بدون فواصل"), "[عنوان محمي]")
        self.assertEqual(mask_address(""), "")
        self.assertEqual(mask_address(None), "")

    def test_mask_patient_dict_for_non_privileged_user(self):
        data = {
            'id': 'test-uuid',
            'full_name': 'عبدالله خالد المطيري',
            'national_id': '1084729103',
            'phone': '+966551239876',
            'address': 'الدمام - حي الشاطئ',
            'emergency_contact': '+966509998877',
            'age': 35,
        }

        user = MagicMock()
        user.is_authenticated = True
        user.role = 'RECEPTIONIST'

        patient = MagicMock()
        patient.pk = 'test-uuid'

        result = mask_patient_dict(data, user, patient)

        self.assertEqual(result['national_id'], "******9103")
        self.assertEqual(result['phone'], "+9665*****876")
        self.assertEqual(result['full_name'], "عبدالله خ. ****")
        self.assertEqual(result['address'], "الدمام - [عنوان محمي]")
        self.assertEqual(result['emergency_contact'], "+9665*****877")
        self.assertEqual(result['age'], 35)

    def test_unmask_for_admin(self):
        data = {
            'full_name': 'عبدالله خالد المطيري',
            'national_id': '1084729103',
            'phone': '+966551239876',
        }

        user = MagicMock()
        user.is_authenticated = True
        user.role = 'SUPER_ADMIN'

        patient = MagicMock()
        patient.pk = 'test-uuid'

        result = mask_patient_dict(data, user, patient)

        # Admin should see completely unmasked data
        self.assertEqual(result['national_id'], "1084729103")
        self.assertEqual(result['phone'], "+966551239876")
        self.assertEqual(result['full_name'], "عبدالله خالد المطيري")

    def test_sanitize_image_metadata_non_image(self):
        from apps.core.uploads import sanitize_image_metadata
        mock_file = MagicMock()
        mock_file.name = "document.pdf"
        # Should return safely without error
        sanitize_image_metadata(mock_file)
        mock_file.seek.assert_not_called()

