from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _build_default_code_from_variant_attributes(self):
        self.ensure_one()

        degree_parts = []
        normal_parts = []

        ptavs = self.product_template_attribute_value_ids.sorted(
            key=lambda x: (
                x.attribute_line_id.sequence or 0,
                x.product_attribute_value_id.sequence or 0,
                x.id,
            )
        )

        for ptav in ptavs:
            value = ptav.product_attribute_value_id
            attribute = value.attribute_id

            text = (value.name or '').strip()
            if not text:
                continue

            if attribute and attribute.is_degree:
                symbol = attribute.symbol_degree or ''
                text = f'{symbol}{text}' if symbol else text
                degree_parts.append(text)
            else:
                normal_parts.append(text)

        result = []
        if degree_parts:
            result.append(f"({', '.join(degree_parts)})")
        if normal_parts:
            result.append(' '.join(normal_parts))

        return ' '.join(result) if result else False

    def _update_variant_default_code(self):
        for rec in self:
            code = rec._build_default_code_from_variant_attributes()
            rec.default_code = code or False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_variant_default_code()
        return records

    def write(self, vals):
        res = super().write(vals)

        trigger_fields = {
            'product_template_attribute_value_ids',
            'product_no_variant_attribute_value_ids',
        }
        if trigger_fields.intersection(vals.keys()):
            self._update_variant_default_code()

        return res

    def _generate_barcode(self):
        self.ensure_one()

        prefix = (self.categ_id.barcode_prefix or '').strip()
        if not prefix:
            return False

        if not prefix.isdigit():
            raise ValidationError(_('Barcode Prefix phải là số.'))

        if len(prefix) != 5:
            raise ValidationError(_('Barcode Prefix phải gồm đúng 5 số.'))

        running_number = self.env['ir.sequence'].sudo().next_by_code(
            'product.template.barcode.running'
        )
        if not running_number:
            raise ValidationError(_('Không tìm thấy sequence sinh code'))

        running_number = str(running_number).zfill(7)[-7:]

        base12 = f'{prefix}{running_number}'
        check_digit = self._calculate_ean13_check_digit(base12)

        return f'{base12}{check_digit}'

    def _calculate_ean13_check_digit(self, base12):
        if len(base12) != 12 or not base12.isdigit():
            raise ValidationError(_('Chuỗi tính EAN-13 phải gồm đúng 12 chữ số.'))

        total = 0
        for index, char in enumerate(base12):
            digit = int(char)
            if (index + 1) % 2 == 0:
                total += digit * 3
            else:
                total += digit

        return str((10 - (total % 10)) % 10)

    def _generate_barcode_for_variants_if_needed(self):
        for rec in self:
            variants = rec.product_variant_ids.filtered(lambda v: v.active)

            for variant in variants:
                if variant.barcode:
                    continue

                barcode = rec._generate_barcode()
                if barcode:
                    variant.barcode = barcode
            if len(variants) <= 1:
                continue

            for variant in variants:
                if variant.barcode:
                    continue

                barcode = rec._generate_barcode()
                if barcode:
                    variant.barcode = barcode

    @api.constrains('barcode')
    def _check_unique_barcode(self):
        for rec in self:
            barcode = (rec.barcode or '').strip()
            if not barcode:
                continue

            if not barcode.isdigit():
                raise ValidationError(_('Mã vạch chỉ được nhập số.'))

            if len(barcode) != 13:
                raise ValidationError(_('Mã vạch phải gồm đúng 13 số.'))

            duplicate = self.search([
                ('id', '!=', rec.id),
                ('barcode', '=', barcode),
            ], limit=1)

            if duplicate:
                raise ValidationError(_('Mã vạch không được trùng nhau.'))