"""
Tests for the marketplace app — Categories, Listings CRUD, Images, Reactions, Bookmarks.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.marketplace.models import MarketplaceCategory, MarketplaceListing


def make_user(email="seller@market.ng", password="marketpass123", **kwargs):
    defaults = {"full_name": "Market Seller", "user_type": User.UserType.FARMER}
    defaults.update(kwargs)
    return User.objects.create_user(email=email, password=password, **defaults)


def make_category(name="Livestock", slug="livestock"):
    return MarketplaceCategory.objects.create(name=name, slug=slug)


def make_listing(seller, category=None, **kwargs):
    defaults = {
        "title": "50 Day-Old Broiler Chicks",
        "description": "Healthy Ross breed broiler chicks",
        "price": "22500.00",
        "location": "Dawakin Kudu",
        "status": "available",
    }
    defaults.update(kwargs)
    return MarketplaceListing.objects.create(seller=seller, category=category, **defaults)


class CategoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/marketplace/categories/"
        self.category = make_category()

    def test_list_categories_public(self):
        """Categories are publicly accessible without authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_categories_are_read_only(self):
        """Categories cannot be created via the API (ReadOnlyModelViewSet)."""
        self.client.force_authenticate(user=make_user())
        response = self.client.post(self.url, {"name": "Equipment", "slug": "equipment"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ListingCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/marketplace/listings/"
        self.seller = make_user()
        self.buyer = make_user(email="buyer@market.ng")
        self.category = make_category()
        self._login_as(self.seller)

    def _login_as(self, user, password="marketpass123"):
        resp = self.client.post(
            "/api/v1/auth/token/",
            {"email": user.email, "password": password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_create_listing(self):
        data = {
            "title": "100 Bags of Maize",
            "description": "Premium quality maize for animal feed",
            "price": "45000.00",
            "location": "Kano Municipal",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "100 Bags of Maize")
        self.assertEqual(response.data["seller"], str(self.seller))

    def test_list_listings_public(self):
        """Listing index is publicly accessible."""
        make_listing(self.seller, self.category)
        self.client.credentials()  # no auth
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_listing_public(self):
        listing = make_listing(self.seller)
        self.client.credentials()
        response = self.client.get(f"{self.url}{listing.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], listing.title)

    def test_update_listing_by_owner(self):
        listing = make_listing(self.seller)
        response = self.client.patch(
            f"{self.url}{listing.id}/",
            {"title": "Updated Title"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listing.refresh_from_db()
        self.assertEqual(listing.title, "Updated Title")

    def test_update_listing_by_other_user_is_forbidden(self):
        listing = make_listing(self.seller)
        self._login_as(self.buyer)
        response = self.client.patch(
            f"{self.url}{listing.id}/",
            {"title": "Hijack Attempt"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_listing_by_owner(self):
        listing = make_listing(self.seller)
        response = self.client.delete(f"{self.url}{listing.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_listing_by_other_user_is_forbidden(self):
        listing = make_listing(self.seller)
        self._login_as(self.buyer)
        response = self.client.delete(f"{self.url}{listing.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_soft_deleted_listing_not_in_list(self):
        listing = make_listing(self.seller)
        listing.is_deleted = True
        listing.save()
        response = self.client.get(self.url)
        payload = response.data
        results = payload.get("results") if isinstance(payload, dict) else payload
        ids = [str(item["id"]) for item in (results or [])]
        self.assertNotIn(str(listing.id), ids)

    def test_create_listing_unauthenticated(self):
        self.client.credentials()
        data = {"title": "Test", "description": "Test", "price": "100.00"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_listings(self):
        make_listing(self.seller, title="Goat for sale", description="Healthy Sahel goat")
        make_listing(self.seller, title="Chicken feed bags", description="Quality broiler starter")
        response = self.client.get(f"{self.url}?search=goat")
        results = response.data.get("results") or response.data
        self.assertGreaterEqual(len(results), 1)
        self.assertTrue(any("Goat" in r["title"] for r in results))


class ListingReactionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.seller = make_user()
        self.buyer = make_user(email="buyer@market.ng")
        self.listing = make_listing(self.seller)
        self._login_as(self.buyer)

    def _login_as(self, user, password="marketpass123"):
        resp = self.client.post(
            "/api/v1/auth/token/",
            {"email": user.email, "password": password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_like_listing(self):
        url = f"/api/v1/marketplace/listings/{self.listing.id}/like/"
        response = self.client.post(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.reactions.filter(reaction="like").count(), 1)

    def test_bookmark_listing(self):
        url = f"/api/v1/marketplace/listings/{self.listing.id}/bookmark/"
        response = self.client.post(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertEqual(self.listing.bookmarks.count(), 1)
