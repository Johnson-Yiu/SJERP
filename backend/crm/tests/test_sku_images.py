from io import BytesIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.http import Http404
from django.test import RequestFactory, SimpleTestCase
from PIL import Image

from crm.services.sku_images import thumbnail_response
from crm.serializers import SKUSerializer


class SKUThumbnailTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.storage = FileSystemStorage(location=self.directory.name)
        cache.clear()
        self.request = RequestFactory().get('/api/skus/1/thumbnail/')

    def image(self, name='old.gif', color='red'):
        data = BytesIO()
        Image.new('RGB', (1200, 600), color).save(
            data, format='GIF', save_all=True,
            append_images=[Image.new('RGB', (1200, 600), 'blue')], duration=100,
        )
        name = self.storage.save(name, ContentFile(data.getvalue()))
        return SimpleNamespace(name=name, storage=self.storage)

    def test_existing_animated_image_becomes_small_static_thumbnail_and_is_cached(self):
        field = self.image()
        response = thumbnail_response(field, self.request)
        with Image.open(BytesIO(response.content)) as thumb:
            self.assertEqual(thumb.size, (84, 42))
            self.assertEqual(thumb.format, 'WEBP')
            self.assertEqual(getattr(thumb, 'n_frames', 1), 1)
        with patch.object(self.storage, 'open', side_effect=AssertionError('Decoded again')):
            self.assertEqual(thumbnail_response(field, self.request).content, response.content)
            request = RequestFactory().get('/', HTTP_IF_NONE_MATCH=response['ETag'])
            self.assertEqual(thumbnail_response(field, request).status_code, 304)

    def test_replacement_changes_url_and_thumbnail(self):
        old, new = self.image(), self.image('replacement.gif', 'green')
        serializer = SKUSerializer()
        self.assertNotEqual(
            serializer.get_image_thumbnail(SimpleNamespace(pk=1, image=old)),
            serializer.get_image_thumbnail(SimpleNamespace(pk=1, image=new)),
        )
        self.assertNotEqual(thumbnail_response(old, self.request).content,
                            thumbnail_response(new, self.request).content)

    def test_missing_or_invalid_image_does_not_return_original(self):
        self.assertEqual(SKUSerializer().get_image_thumbnail(SimpleNamespace(image=None)), '')
        with self.assertRaises(Http404):
            thumbnail_response(None, self.request)
        name = self.storage.save('broken.png', ContentFile(b'broken'))
        with self.assertRaises(Http404):
            thumbnail_response(SimpleNamespace(name=name, storage=self.storage), self.request)
