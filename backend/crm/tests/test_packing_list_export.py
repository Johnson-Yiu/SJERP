from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.core.files.base import ContentFile
from openpyxl import load_workbook
from PIL import Image as PILImage
from rest_framework.test import APIClient

from crm.models import (
    AccessRole,
    Customer,
    EmployeeProfile,
    HSCode,
    InventoryMovement,
    Order,
    OrderItem,
    OrganizationUnit,
    Position,
    Product,
    RolePermission,
    ShipmentPackage,
    ShipmentPackageItem,
    SKU,
)
from crm.services.fulfillment import confirm_shipment
from crm.services.packing_list import TEMPLATE_PATH


class PackingListExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="C-PL-01", name="Packing List Customer")
        hs_code = HSCode.objects.create(code="9405420000", description="LED lighting")
        product = Product.objects.create(code="P-PL-01", name="Packing Product", name_en="Packing Product", hs_code=hs_code)
        self.sku_a = SKU.objects.create(
            product=product,
            sku="PL-A",
            display_name_cn="灯具 A",
            description_en="LED lamp A",
            unit="pcs",
        )
        self.sku_b = SKU.objects.create(
            product=product,
            sku="PL-B",
            display_name_cn="灯具 B",
            description_en="LED lamp B",
            unit="pcs",
        )
        self.order = Order.objects.create(
            order_no="SO-PL-01",
            customer=self.customer,
            order_date=date(2026, 10, 21),
            status="confirmed",
        )
        item_a = OrderItem.objects.create(order=self.order, sku=self.sku_a, quantity="5", unit_price="10")
        item_b = OrderItem.objects.create(order=self.order, sku=self.sku_b, quantity="4", unit_price="20")
        for sku in (self.sku_a, self.sku_b):
            InventoryMovement.objects.create(
                movement_no=f"IN-{sku.sku}",
                movement_date=date(2026, 10, 21),
                type="adjust_in",
                sku=sku,
                quantity="100",
            )
        self.shipment = confirm_shipment(
            self.order,
            {
                "shipment_no": "SH-PL-01",
                "shipment_date": date(2026, 10, 21),
                "items": [
                    {"order_item": item_a.pk, "quantity": "5"},
                    {"order_item": item_b.pk, "quantity": "4"},
                ],
            },
        )
        self.url = f"/api/shipments/{self.shipment.pk}/export-packing-list/"

    def package(self, carton_no, items, *, length="40", width="30", height="20", net="1.2", gross="1.5"):
        package = ShipmentPackage.objects.create(
            shipment=self.shipment,
            carton_no=carton_no,
            length=length,
            width=width,
            height=height,
            actual_net_weight=net,
            actual_gross_weight=gross,
        )
        ShipmentPackageItem.objects.bulk_create(
            [ShipmentPackageItem(shipment_package=package, sku_id=sku_id, quantity=quantity) for sku_id, quantity in items]
        )
        return package

    def full_mixed_packing(self):
        self.package(1, [(self.sku_a.pk, "3")])
        self.package(2, [(self.sku_a.pk, "2"), (self.sku_b.pk, "4")], length="50", width="40", height="30", net="2", gross="2.5")

    def test_export_uses_real_shipment_and_preserves_template_structure(self):
        self.full_mixed_packing()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data if hasattr(response, "data") else response.content[:200])
        self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertIn("PackingList-SH-PL-01.xlsx", response["Content-Disposition"])

        workbook = load_workbook(BytesIO(response.content), data_only=False)
        sheet = workbook.active
        self.assertEqual(sheet.max_column, 16)
        self.assertIsNone(sheet["B1"].value)
        self.assertEqual(sheet["C1"].value, "SH-PL-01")
        self.assertIsNone(sheet["B2"].value)
        self.assertEqual(sheet["C2"].value, "2026-10-21")
        self.assertEqual(sheet["A3"].value, "Invoice Ref No.:")
        self.assertIsNone(sheet["B3"].value)
        self.assertIsNone(sheet["C3"].value)
        self.assertEqual(sheet["D3"].value, "Sales Order Ref.:")
        self.assertEqual(sheet["F3"].value, "SO-PL-01")
        self.assertEqual(sheet["A4"].value, "No.")
        self.assertEqual(sheet["A5"].value, "序号")
        self.assertEqual(sheet["F6"].value, "9405420000")
        self.assertEqual(sheet["E6"].value, Decimal("3"))
        self.assertEqual(sheet["E7"].value, Decimal("2"))
        self.assertEqual(sheet["E8"].value, Decimal("4"))
        self.assertEqual(sheet["H6"].value, 1)
        self.assertEqual(sheet["H7"].value, 1)
        self.assertIsNone(sheet["H8"].value)
        self.assertEqual(sheet["M6"].value, '=IF(OR(L6="",H6=""),"",L6*H6)')
        self.assertEqual(sheet["O7"].value, '=IF(OR(N7="",H7=""),"",N7*H7)')
        self.assertGreaterEqual(sheet.row_dimensions[6].height, 53)
        self.assertTrue(str(sheet.print_area).endswith("$A$1:$P$15"))
        self.assertEqual(sheet.print_title_rows.replace("$", ""), "4:5")
        self.assertEqual(sheet.page_setup.orientation, "landscape")
        self.assertEqual(str(sheet.page_setup.paperSize), "9")
        self.assertEqual(sheet["H15"].value, "=SUM(H6:H14)")
        self.assertEqual(sheet["M15"].value, "=SUM(M6:M14)")
        self.assertEqual(sheet["O15"].value, "=SUM(O6:O14)")
        self.assertEqual(sheet["P15"].value, "=SUM(P6:P14)")
        self.assertEqual(sheet.oddFooter.center.text, "Page &P of &N")

        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            names = set(archive.namelist())
            self.assertIn("xl/media/image1.png", names)
            self.assertIn("xl/drawings/vmlDrawing1.vml", names)
            self.assertIn("xl/drawings/_rels/vmlDrawing1.vml.rels", names)
            sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
            self.assertIn("legacyDrawingHF", sheet_xml)
            self.assertIn("Page &amp;P of &amp;N", sheet_xml)

    def test_long_description_and_notes_use_dynamic_height_without_truncation(self):
        order_item = self.order.items.get(sku=self.sku_a)
        long_description = (
            "Professional recessed LED luminaire with a long English model description "
            "and mixed 中文规格参数，包含安装方式、功率、色温以及包装说明。"
        )
        order_item.description_snapshot = long_description
        order_item.save(update_fields=["description_snapshot"])
        self.package(1, [(self.sku_a.pk, "5")], net="1.2", gross="1.5")
        package = self.shipment.packages.get(carton_no=1)
        package.notes = "请保持每个纸箱标签完整，备注包含较长的装箱说明和客户定制要求。"
        package.save(update_fields=["notes"])
        self.package(2, [(self.sku_b.pk, "4")])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        sheet = load_workbook(BytesIO(response.content), data_only=False).active
        self.assertIn(long_description, sheet["D6"].value)
        self.assertIn("请保持每个纸箱标签完整", sheet["D6"].value)
        self.assertGreater(sheet.row_dimensions[6].height, 90)

    @staticmethod
    def _image_bytes(color):
        output = BytesIO()
        image = PILImage.new("RGB", (16, 16), color)
        image.save(output, format="PNG")
        return output.getvalue()

    def test_product_images_keep_template_logo_and_relationships(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.sku_a.image.save("sku-a.png", ContentFile(self._image_bytes("red")), save=True)
            self.sku_b.image.save("sku-b.png", ContentFile(self._image_bytes("blue")), save=True)
            self.full_mixed_packing()

            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)

            with zipfile.ZipFile(BytesIO(response.content)) as archive, zipfile.ZipFile(TEMPLATE_PATH) as template:
                names = set(archive.namelist())
                template_logo = template.read("xl/media/image1.png")
                self.assertEqual(archive.read("xl/media/image1.png"), template_logo)
                product_media = sorted(
                    name for name in names if name.startswith("xl/media/") and name != "xl/media/image1.png"
                )
                self.assertGreaterEqual(len(product_media), 2)

                rels = ET.fromstring(archive.read("xl/drawings/_rels/drawing1.xml.rels"))
                rel_map = {node.attrib["Id"]: node.attrib["Target"] for node in rels}
                self.assertNotIn("../media/image1.png", rel_map.values())

                xdr_ns = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
                a_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
                r_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                drawing = ET.fromstring(archive.read("xl/drawings/drawing1.xml"))
                colors_by_row = {}
                for anchor in drawing:
                    row_node = anchor.find(f"{{{xdr_ns}}}from/{{{xdr_ns}}}row")
                    embed = anchor.find(f".//{{{a_ns}}}blip")
                    if row_node is None or embed is None:
                        continue
                    target = rel_map[embed.attrib[f"{{{r_ns}}}embed"]]
                    media_name = "xl/media/" + Path(target).name
                    pixel = PILImage.open(BytesIO(archive.read(media_name))).convert("RGB").getpixel((0, 0))
                    colors_by_row[int(row_node.text) + 1] = pixel
                self.assertTrue(any(pixel[0] > 200 and pixel[1] < 80 for pixel in colors_by_row.values()))
                self.assertTrue(any(pixel[2] > 200 and pixel[0] < 80 for pixel in colors_by_row.values()))

                vml_rels = ET.fromstring(archive.read("xl/drawings/_rels/vmlDrawing1.vml.rels"))
                self.assertIn("../media/image1.png", {node.attrib.get("Target") for node in vml_rels})

    def test_same_sku_same_carton_shape_is_grouped_without_losing_quantity(self):
        self.order.items.filter(sku=self.sku_b).update(quantity="0.01")
        self.shipment.items.filter(sku=self.sku_b).update(quantity="0.01")
        self.package(1, [(self.sku_a.pk, "2")])
        self.package(2, [(self.sku_a.pk, "2")])
        self.package(3, [(self.sku_a.pk, "1")])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        # The shipment still needs the B line packed; do not let a test fixture
        # accidentally turn a quantity mismatch into a successful export.
        self.package(4, [(self.sku_b.pk, "0.01")])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        sheet = load_workbook(BytesIO(response.content), data_only=False).active
        self.assertEqual(sheet["E6"].value, Decimal("4"))
        self.assertEqual(sheet["G6"].value, Decimal("2"))
        self.assertEqual(sheet["H6"].value, 2)
        self.assertIn("CTN-001–CTN-002", sheet["D6"].value)

    def test_quantity_mismatch_returns_per_sku_difference_and_does_not_write(self):
        self.package(1, [(self.sku_a.pk, "5"), (self.sku_b.pk, "3")], net="1", gross="1.2")
        before = list(self.shipment.packages.values_list("id", "carton_no"))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["differences"], [{
            "sku_id": self.sku_b.pk,
            "sku": "PL-B",
            "shipped_quantity": "4",
            "packed_quantity": "3",
            "difference": "1",
        }])
        self.assertEqual(list(self.shipment.packages.values_list("id", "carton_no")), before)

    def test_missing_physical_values_are_blank_not_invented(self):
        self.package(1, [(self.sku_a.pk, "5")], length=None, width=None, height=None, net="0", gross="0")
        self.package(2, [(self.sku_b.pk, "4")], length=None, width=None, height=None, net="0", gross="0")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        sheet = load_workbook(BytesIO(response.content), data_only=False).active
        self.assertIsNone(sheet["I6"].value)
        self.assertIsNone(sheet["L6"].value)
        self.assertIsNone(sheet["N6"].value)
        self.assertEqual(sheet["M6"].value, '=IF(OR(L6="",H6=""),"",L6*H6)')

    def test_missing_shipment_movement_uses_order_snapshot_without_failing(self):
        self.shipment.items.update(inventory_movement=None)
        self.package(1, [(self.sku_a.pk, "5")])
        self.package(2, [(self.sku_b.pk, "4")])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        sheet = load_workbook(BytesIO(response.content), data_only=False).active
        self.assertIn("PL-A", sheet["D6"].value)
        self.assertIn("LED lamp A", sheet["D6"].value)

    def test_cancelled_shipment_is_blocked(self):
        self.full_mixed_packing()
        self.shipment.status = "cancelled"
        self.shipment.save(update_fields=["status"])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("已确认发货单", response.data["detail"])


@override_settings(APP_STAGE="production", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
class PackingListExportPermissionTests(PackingListExportTests):
    def setUp(self):
        super().setUp()
        unit = OrganizationUnit.objects.create(name="Packing UAT", code="PL-UAT")
        position = Position.objects.create(unit=unit, name="采购", code="PL-UAT-POS")
        role = AccessRole.objects.create(name="Packing 导出", code="pl-export")
        RolePermission.objects.create(role=role, module="orders", can_view=True)
        RolePermission.objects.create(role=role, module="skus", can_view=True)
        RolePermission.objects.create(role=role, module="hs_codes", can_view=True)
        RolePermission.objects.create(role=role, module="inventory", can_view=True, can_export=True)
        user = get_user_model().objects.create_user(username="packing-exporter", password="test-password")
        profile = EmployeeProfile.objects.create(user=user, display_name="Packing Exporter", unit=unit, position=position)
        profile.roles.add(role)
        self.customer.owner_profile = profile
        self.customer.save(update_fields=["owner_profile"])
        self.client.force_authenticate(user=user)

    def test_export_requires_inventory_export_permission(self):
        self.full_mixed_packing()
        RolePermission.objects.filter(role__code="pl-export", module="inventory").update(can_export=False)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_export_blanks_hs_code_without_hs_code_permission(self):
        self.full_mixed_packing()
        RolePermission.objects.filter(role__code="pl-export", module="hs_codes").update(can_view=False)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(load_workbook(BytesIO(response.content), data_only=False).active["F6"].value)
