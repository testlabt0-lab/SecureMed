"""Encryption at rest for everything under MEDIA_ROOT.

The database columns holding PHI are encrypted (``apps.security.crypto``), but the
files were not: ``medical_files/<channel>/<uuid>.pdf`` — imaging, lab reports,
scanned consent forms — sat on the instance disk as plaintext, readable by anything
with filesystem access: a backup snapshot, a mounted volume, a support engineer, or
a path-traversal bug anywhere else in the process.

This is deliberately implemented at the ``Storage`` layer rather than on the model.
``FileField`` calls ``storage._save()`` on write and ``storage._open()`` on read, so
swapping the backend in ``STORAGES['default']`` encrypts every existing FileField —
``patients.MedicalFile.file``, ``telemedicine.ChatMessage.attachment``, and anything
added later — with **no migration and no model change**. Names, paths and URLs are
untouched; only the bytes on disk differ.

Two consequences worth knowing:

* Reads are transparent but not free — a file is decrypted in memory, so this is
  suited to the 20 MB ceiling ``validate_file_size`` enforces, not to video.
* Anything that reads MEDIA_ROOT *without* going through the storage API gets
  ciphertext. There is exactly one such place left, ``django.views.static.serve``,
  and ``apps.core.media.ProtectedMediaView`` no longer uses it. Do not reintroduce
  ``static()`` for MEDIA_URL in production; ``config/urls.py`` routes it through
  ``ProtectedMediaView`` instead, which it should be doing anyway since ``serve()``
  applies no authorisation.
"""
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage

from apps.security.crypto import (
    MEDIA_HEADER_LEN,
    MEDIA_MAGIC_LEN,
    decrypt_media,
    encrypt_media,
    is_encrypted_media,
)


def media_encryption_enabled():
    """Whether *new* uploads are encrypted.

    Defaults to on whenever DEBUG is off, so a deployment does not have to opt in
    to protecting patient files. Reads never consult this flag — they detect the
    header per file — so turning it off stops encrypting new uploads without
    orphaning anything already written.
    """
    return bool(getattr(settings, 'ENCRYPT_MEDIA_AT_REST', not settings.DEBUG))


class EncryptedFileSystemStorage(FileSystemStorage):
    """FileSystemStorage that encrypts on write and decrypts on read."""

    def _save(self, name, content):
        if not media_encryption_enabled():
            return super()._save(name, content)

        # DRF and Django both hand over a File that may already have been read
        # once — by a validator sniffing magic bytes, or by an earlier size check.
        if hasattr(content, 'seek'):
            try:
                content.seek(0)
            except (OSError, ValueError):
                pass

        raw = content.read()
        if isinstance(raw, str):
            raw = raw.encode('utf-8')

        # Guard against double encryption. Re-saving a model instance whose file
        # was read back through _open() gives plaintext, so this should not
        # trigger; a management command that copies raw bytes between storages
        # would, and encrypting twice makes the file unreadable by every normal
        # path through this class.
        if is_encrypted_media(raw):
            return super()._save(name, ContentFile(raw))

        return super()._save(name, ContentFile(encrypt_media(raw)))

    def _open(self, name, mode='rb'):
        fh = super()._open(name, mode)
        try:
            blob = fh.read()
        finally:
            fh.close()

        if isinstance(blob, str):
            # Opened in text mode by a caller that did not expect ciphertext.
            # Nothing in this project does, but returning the bytes it asked for
            # is better than a confusing TypeError deeper in.
            return ContentFile(blob.encode('utf-8'), name=name)

        if not is_encrypted_media(blob):
            # Uploaded before this backend existed, or while the setting was off.
            return ContentFile(blob, name=name)

        return ContentFile(decrypt_media(blob), name=name)

    def size(self, name):
        """Plaintext length, not the on-disk length.

        ``FileField.size`` delegates here once a file is committed, and it feeds
        ``Content-Length`` on downloads and the size shown in the UI. Reporting the
        ciphertext length would overstate every encrypted file by the header and
        leave the browser waiting for bytes that never arrive.
        """
        on_disk = super().size(name)
        if on_disk < MEDIA_HEADER_LEN:
            return on_disk
        with super()._open(name, 'rb') as fh:
            header = fh.read(MEDIA_MAGIC_LEN)
        if not is_encrypted_media(header):
            return on_disk
        return on_disk - MEDIA_HEADER_LEN
