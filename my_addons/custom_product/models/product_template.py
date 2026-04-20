from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    export_bill = fields.Boolean(string='Xuất hóa đơn', default=True)
    name_bill = fields.Text(string='Tên xuất hóa đơn')
    is_attr = fields.Boolean(string='Có tồn tại thuộc tính', compute='_compute_is_attr', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ProductTemplate, self).create(vals_list)
        for rec, vals in zip(records, vals_list):
            if rec.is_attr:
                continue

            if vals.get('barcode'):
                continue

            barcode = rec._generate_barcode()
            if barcode:
                rec.barcode = barcode
        records._sync_attribute_line_sequence_by_category()
        records._generate_barcode_for_variants_if_needed()
        return records

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if vals.get('barcode'):
            self._sync_attribute_line_sequence_by_category()
            self._generate_barcode_for_variants_if_needed()
            return res

        for rec in self:
            if rec.is_attr:
                continue

            if not rec.barcode:
                barcode = rec._generate_barcode()
                if barcode:
                    rec.barcode = barcode

        self._sync_attribute_line_sequence_by_category()
        self._generate_barcode_for_variants_if_needed()
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

            duplicate = self.search([
                ('id', '!=', rec.id),
                ('barcode', '=', barcode),
            ], limit=1)

            if duplicate:
                raise ValidationError(_('Mã vạch không được trùng nhau.'))

            if not barcode.isdigit():
                raise ValidationError(_('Mã vạch chỉ được chưa các số.'))

            if len(barcode) != 13:
                raise ValidationError(_('Mã vạch phải gồm đúng 13 số.'))


    @api.depends('categ_id')
    def _compute_is_attr(self):
        for rec in self:
            rec.is_attr = bool(rec.categ_id.attr_ids)

    @api.constrains('categ_id', 'attribute_line_ids', 'attribute_line_ids.attribute_id')
    def _check_attribute_line_ids_by_category_config(self):
        for rec in self:
            category = rec.categ_id
            if not category or not category.attr_ids:
                continue

            if not rec.attribute_line_ids:
                raise ValidationError(
                    _('Danh mục này có cấu hình thuộc tính, bắt buộc phải khai báo thông tin Thuộc tính & Biến thể.'))

            category_attrs = category.attr_ids.mapped('attribute_id')
            product_attrs = rec.attribute_line_ids.mapped('attribute_id')

            category_attr_ids = set(category_attrs.ids)
            product_attr_ids = set(product_attrs.ids)

            missing_attr_ids = category_attr_ids - product_attr_ids
            extra_attr_ids = product_attr_ids - category_attr_ids

            if missing_attr_ids or extra_attr_ids:
                message_parts = []

                if missing_attr_ids:
                    missing_names = category_attrs.filtered(lambda a: a.id in missing_attr_ids).mapped('name')
                    message_parts.append(_('Thiếu thuộc tính bắt buộc theo danh mục: %s') % ', '.join(missing_names))

                if extra_attr_ids:
                    extra_names = product_attrs.filtered(lambda a: a.id in extra_attr_ids).mapped('name')
                    message_parts.append(_('Thuộc tính không thuộc cấu hình danh mục: %s') % ', '.join(extra_names))

                raise ValidationError('\n'.join(message_parts))

    def _sync_attribute_line_sequence_by_category(self):
        for rec in self:
            if not rec.categ_id or not rec.categ_id.attr_ids or not rec.attribute_line_ids:
                continue

            config_sequence_map = {line.attribute_id.id: line.sequence for line in rec.categ_id.attr_ids if
                                   line.attribute_id}

            for attr_line in rec.attribute_line_ids:
                new_sequence = config_sequence_map.get(attr_line.attribute_id.id)
                if new_sequence is not None and attr_line.sequence != new_sequence:
                    attr_line.write({'sequence': new_sequence})
