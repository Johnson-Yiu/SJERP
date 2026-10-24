from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from crm.country_registry import AmbiguousCountryError, CountryNotFoundError, country_options, country_label, resolve_country_code
from crm.models import Contact, Customer, Quote
from crm.quote_numbers import allocate_revision_quote_no, allocate_root_quote_no
from crm.serializers import CustomerSerializer


class CountryRegistryTests(TestCase):
    def test_common_names_codes_aliases_and_spacing_resolve_to_alpha2(self):
        expected = {
            "美国": "US", "united states": "US", "US": "US", "USA": "US",
            "DE": "DE", "  se  ": "SE", "AT": "AT", "瑞典": "SE",
        }
        for value, code in expected.items():
            with self.subTest(value=value):
                self.assertEqual(resolve_country_code(value), code)

    def test_ambiguous_and_unknown_values_are_not_guessed(self):
        with self.assertRaises(AmbiguousCountryError):
            resolve_country_code("America")
        with self.assertRaises(CountryNotFoundError):
            resolve_country_code("Atlantis")

    def test_catalog_shows_standard_english_name_and_alpha2_and_searches_america(self):
        united_states = next(option for option in country_options() if option["value"] == "US")
        self.assertEqual(united_states["label"], "United States / US")
        self.assertIn("america", united_states["searchText"])
        self.assertEqual(country_label("us"), "United States / US")


class CustomerCountryApiTests(APITestCase):
    def test_explicit_known_country_is_saved_as_alpha2_and_exposed_with_display_label(self):
        response = self.client.post("/api/customers/", {
            "name": "Country Picker Buyer",
            "country": "  us ",
            "contacts": [{"name": "Buyer Contact"}],
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        customer = Customer.objects.get(name="Country Picker Buyer")
        self.assertEqual(customer.country, "US")
        self.assertEqual(response.data["country_display"], "United States / US")

    def test_ambiguous_and_unknown_business_input_is_rejected(self):
        for country in ("America", "Atlantis"):
            with self.subTest(country=country):
                response = self.client.post("/api/customers/", {
                    "name": f"Invalid {country}",
                    "country": country,
                    "contacts": [{"name": "Buyer Contact"}],
                }, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("country", response.data)

    def test_unknown_import_text_is_preserved_for_manual_review(self):
        serializer = CustomerSerializer(
            data={"name": "Imported Legacy Buyer", "country": "旧国家文本"},
            context={"allow_import_without_contacts": True},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        customer = serializer.save()
        self.assertEqual(customer.country, "旧国家文本")

    def test_country_catalog_is_local_and_includes_standard_candidates(self):
        response = self.client.get("/api/customers/country-catalog/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(next(row for row in response.data if row["value"] == "DE")["label"], "Germany / DE")
        self.assertEqual(next(row for row in response.data if row["value"] == "SE")["label"], "Sweden / SE")
        self.assertEqual(next(row for row in response.data if row["value"] == "AT")["label"], "Austria / AT")


class CountryQuoteCompatibilityTests(TestCase):
    def test_legacy_quote_number_stays_immutable_after_customer_country_selection(self):
        customer = Customer.objects.create(code="C-ISS008", name="History Buyer", country="Germany")
        root_number = allocate_root_quote_no(date(2026, 8, 21), customer.country)
        root = Quote.objects.create(quote_no=root_number, customer=customer, quote_date=date(2026, 8, 21))

        customer.country = "US"
        customer.save(update_fields=["country"])
        revision_number, revision_no = allocate_revision_quote_no(root)

        self.assertEqual(root_number, "SJ20260821DE001")
        self.assertEqual(root.quote_no, "SJ20260821DE001")
        self.assertEqual((revision_number, revision_no), ("SJ20260821DE001-1", 1))

    def test_alpha2_sequences_remain_unique_per_date_and_country(self):
        self.assertEqual(allocate_root_quote_no(date(2026, 8, 22), "DE"), "SJ20260822DE001")
        self.assertEqual(allocate_root_quote_no(date(2026, 8, 22), "Germany"), "SJ20260822DE002")
        self.assertEqual(allocate_root_quote_no(date(2026, 8, 22), "AT"), "SJ20260822AT001")
