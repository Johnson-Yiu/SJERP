from datetime import date, timedelta
from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import Product, ProductCertificate
from crm.serializers import ProductCertificateSerializer


class CertificateExpiryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = date(2026, 10, 7)
        self.product = Product.objects.create(code="P-CERT-UAT", name="Certificate light")
        self.other = Product.objects.create(code="P-CERT-OTHER", name="Other light")
        self.rows = {}
        for days in [None, -100, -1, 0, 1, 30, 31, 90, 91]:
            self.rows[days] = ProductCertificate.objects.create(product=self.product, name=f"CE {days}", expires_on=self.today + timedelta(days=days) if days is not None else None)
        self.clock = patch("django.utils.timezone.localdate", return_value=self.today)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def results(self, **query):
        response = self.client.get("/api/product-certificates/", query)
        self.assertEqual(response.status_code, 200)
        return response.data["results"] if isinstance(response.data, dict) else response.data

    def test_status_boundaries_and_signed_days(self):
        for days, expected in [(None,"no_expiry"),(-1,"expired"),(0,"expiring_30"),(1,"expiring_30"),(30,"expiring_30"),(31,"expiring_90"),(90,"expiring_90"),(91,"valid")]:
            with self.subTest(days=days):
                result = ProductCertificateSerializer(self.rows[days]).data
                self.assertEqual(result["expiry_status"], expected)
                self.assertEqual(result["days_to_expiry"], days)
                self.assertEqual(result["expiry_status_display"], "今日到期" if days == 0 else {"no_expiry":"无有效期","expired":"已过期","expiring_30":"30 天内到期","expiring_90":"90 天内到期","valid":"有效"}[expected])

    def test_filters_and_urgent_order(self):
        for expiry, days in [("attention",[-100,-1,0,1,30,31,90]),("expired",[-100,-1]),("expiring",[0,1,30,31,90]),("valid",[91]),("no_expiry",[None])]:
            with self.subTest(expiry=expiry):
                self.assertEqual([r["id"] for r in self.results(expiry=expiry)], [self.rows[d].id for d in days])

    def test_product_and_expiry_combined(self):
        ProductCertificate.objects.create(product=self.other, name="Other CE", expires_on=self.today)
        self.assertEqual(len(self.results(product=self.product.id, expiry="attention")), 7)
        self.assertEqual(len(self.results(product=self.other.id, expiry="expired")), 0)

    def test_unfiltered_order_preserved(self):
        expected = list(ProductCertificate.objects.values_list("id", flat=True))
        self.assertEqual([r["id"] for r in self.results()], expected)

    def test_dashboard_counts_null_exclusion_and_limit(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200)
        summary = response.data["summary"]
        self.assertEqual([summary[k] for k in ["certificate_attention", "certificate_expired", "certificate_expiring"]], [7,2,5])
        alerts = response.data["certificate_alerts"]
        self.assertEqual([r["id"] for r in alerts], [self.rows[d].id for d in [-100,-1,0,1,30]])
        self.assertEqual(alerts[0]["days_to_expiry"], -100)
        self.assertEqual(alerts[0]["product_id"], self.product.id)
        self.assertEqual(alerts[0]["certificate_name"], "CE -100")

    def test_derived_fields_read_only_crud(self):
        response = self.client.post("/api/product-certificates/", {"product":self.product.id,"name":"Read only CE","expires_on":str(self.today),"expiry_status":"valid","days_to_expiry":999}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["expiry_status"], "expiring_30")
        self.assertEqual(response.data["days_to_expiry"], 0)
        pk = response.data["id"]
        updated = self.client.patch(f"/api/product-certificates/{pk}/", {"expires_on":None}, format="json")
        self.assertEqual(updated.data["expiry_status"], "no_expiry")
        self.assertEqual(self.client.delete(f"/api/product-certificates/{pk}/").status_code, 204)

    def test_dashboard_zero_state(self):
        ProductCertificate.objects.exclude(expires_on=None).delete()
        result = self.client.get("/api/dashboard/").data
        self.assertEqual(result["summary"]["certificate_attention"], 0)
        self.assertEqual(result["certificate_alerts"], [])

    def test_invalid_file_url_rejected_without_changing_certificate_and_expiry(self):
        record = self.rows[30]
        url = f'/api/product-certificates/{record.pk}/'
        response = self.client.patch(url, {'name': '不应保存', 'file_url': 'javascript:alert(1)'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('file_url', response.data)
        record.refresh_from_db()
        self.assertEqual(record.name, 'CE 30')
        self.assertEqual(record.file_url, '')
        self.assertEqual(ProductCertificateSerializer(record).data['expiry_status'], 'expiring_30')
        response = self.client.patch(url, {'file_url': 'https://example.com/synthetic.pdf'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['expiry_status'], 'expiring_30')
        # Storing a URL is not evidence of successful download or file authorization.
