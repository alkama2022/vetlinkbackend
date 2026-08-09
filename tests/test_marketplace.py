from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
import io
from rest_framework import status
from rest_framework.test import APITestCase
from PIL import Image

from apps.marketplace.models import MarketplaceBookmark, MarketplaceCategory, MarketplaceImage, MarketplaceListing


User = get_user_model()


class MarketplaceCategoryTests(APITestCase):
    def setUp(self):
        MarketplaceCategory.objects.get_or_create(name="Livestock", slug="livestock")
        MarketplaceCategory.objects.get_or_create(name="Feed & Forage", slug="feed-forage")

    def test_categories_return_plain_array(self):
        response = self.client.get('/api/v1/marketplace/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 2)
        self.assertIn('slug', response.data[0])
        self.assertIn('livestock', [c['slug'] for c in response.data])

    def test_categories_readable_without_authentication(self):
        response = self.client.get('/api/v1/marketplace/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MarketplaceListingTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com',
            password='StrongPass123!',
            full_name='Market Seller',
            is_email_verified=True,
        )
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            password='StrongPass123!',
            full_name='Market Buyer',
            is_email_verified=True,
        )
        self.listing = MarketplaceListing.objects.create(
            seller=self.seller,
            title='Vaccinated goat',
            description='Healthy buck for sale',
            price='45000.00',
            location='Dawakin Kudu',
        )
        self.other_listing = MarketplaceListing.objects.create(
            seller=self.buyer,
            title='Fodder bales',
            description='Fresh grass bales',
            price='3500.00',
        )

    def _create_listing(self, client, title, price):
        return client.post(
            '/api/v1/marketplace/listings/',
            {'title': title, 'description': 'Test listing', 'price': price},
            format='json',
        )

    def test_list_is_readable_without_authentication(self):
        response = self.client.get('/api/v1/marketplace/listings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_listing_serializer_includes_seller_id(self):
        response = self.client.get(f'/api/v1/marketplace/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['seller_id'], str(self.seller.id))

    def test_mine_returns_only_current_users_listings(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.get('/api/v1/marketplace/listings/mine/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.listing.id))

    def test_mine_requires_authentication(self):
        response = self.client.get('/api/v1/marketplace/listings/mine/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_filter_listings_by_seller_id(self):
        response = self.client.get(
            f'/api/v1/marketplace/listings/?seller_id={self.seller.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.listing.id))

    def test_owner_can_update_own_listing(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.patch(
            f'/api/v1/marketplace/listings/{self.listing.id}/',
            {'price': '50000.00'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing.refresh_from_db()
        self.assertEqual(str(self.listing.price), '50000.00')

    def test_non_owner_cannot_update_listing(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.patch(
            f'/api/v1/marketplace/listings/{self.listing.id}/',
            {'price': '100.00'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_listing_via_multipart_with_image(self):
        category = MarketplaceCategory.objects.get_or_create(name="Livestock", slug="livestock")[0]
        img_buffer = io.BytesIO()
        Image.new("RGB", (120, 80), color=(120, 40, 40)).save(img_buffer, format="PNG")
        png = SimpleUploadedFile(
            "photo.png",
            img_buffer.getvalue(),
            content_type="image/png",
        )
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(
            '/api/v1/marketplace/listings/',
            {
                'title': 'Day-old broiler chicks',
                'description': '100 chicks for sale',
                'price': '4500.00',
                'condition': 'new',
                'quantity': '100',
                'unit': 'chicks',
                'negotiable': 'true',
                'location': 'Dawakin Kudu, Kano State',
                'category': str(category.id),
                'images': [png],
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        listing = MarketplaceListing.objects.get(id=response.data['id'])
        self.assertEqual(str(listing.seller_id), str(self.seller.id))
        self.assertEqual(str(listing.category_id), str(category.id))
        self.assertEqual(listing.negotiable, True)
        self.assertEqual(listing.quantity, 100)
        self.assertTrue(MarketplaceImage.objects.filter(listing=listing).exists())
        self.assertEqual(response.data['seller'], str(self.seller))
        self.assertEqual(response.data['seller_id'], str(self.seller.id))


class MarketplaceBookmarkTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com',
            password='StrongPass123!',
            full_name='Market Seller',
            is_email_verified=True,
        )
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            password='StrongPass123!',
            full_name='Market Buyer',
            is_email_verified=True,
        )
        self.listing = MarketplaceListing.objects.create(
            seller=self.seller,
            title='Vaccinated goat',
            description='Healthy buck for sale',
            price='45000.00',
        )

    def test_bookmark_action_creates_bookmark(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(f'/api/v1/marketplace/listings/{self.listing.id}/bookmark/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            MarketplaceBookmark.objects.filter(listing=self.listing, user=self.buyer).exists()
        )

    def test_bookmark_action_is_idempotent(self):
        self.client.force_authenticate(user=self.buyer)
        first = self.client.post(f'/api/v1/marketplace/listings/{self.listing.id}/bookmark/')
        second = self.client.post(f'/api/v1/marketplace/listings/{self.listing.id}/bookmark/')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(MarketplaceBookmark.objects.filter(listing=self.listing).count(), 1)

    def test_bookmark_requires_authentication(self):
        response = self.client.post(f'/api/v1/marketplace/listings/{self.listing.id}/bookmark/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bookmarks_list_returns_only_own(self):
        self.client.force_authenticate(user=self.buyer)
        self.client.post(f'/api/v1/marketplace/listings/{self.listing.id}/bookmark/')
        response = self.client.get('/api/v1/marketplace/bookmarks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(str(response.data['results'][0]['listing']), str(self.listing.id))

    def test_unbookmark_deletes_bookmark(self):
        self.client.force_authenticate(user=self.buyer)
        created = self.client.post(f'/api/v1/marketplace/listings/{self.listing.id}/bookmark/')
        bookmark_id = created.data['id']
        response = self.client.delete(f'/api/v1/marketplace/bookmarks/{bookmark_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            MarketplaceBookmark.objects.filter(listing=self.listing, user=self.buyer).exists()
        )
