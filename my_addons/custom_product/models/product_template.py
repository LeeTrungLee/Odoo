from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    export_bill = fields.Boolean(string='Xuất hóa đơn', default=True)
    name_bill = fields.Char(string='Tên xuất hóa đơn')
    is_attr = fields.Boolean(string='Có tồn tại thuộc tính', compute='_compute_is_attr', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            categ_id = vals.get('categ_id')
            if not categ_id:
                continue

            categ = self.env['product.category'].browse(categ_id)
            if categ and categ.attr_ids:
                vals['barcode'] = False

        records = super(ProductTemplate, self).create(vals_list)

        for rec, vals in zip(records, vals_list):
            if rec.is_attr:
                if rec.barcode:
                    rec.write({'barcode': False})
                continue

            if vals.get('barcode'):
                continue

            if not rec.barcode:
                barcode = rec._generate_barcode()
                if barcode:
                    rec.write({'barcode': barcode})

        records._sync_attribute_line_sequence_by_category()
        records._generate_barcode_for_variants_if_needed()
        return records

    def write(self, vals):
        new_barcode = None
        if 'barcode' in vals:
            new_barcode = (vals.get('barcode') or '').strip()

        if vals.get('categ_id'):
            categ = self.env['product.category'].browse(vals['categ_id'])
            if categ and categ.attr_ids:
                vals['barcode'] = False

        if 'barcode' in vals:
            for rec in self:
                if rec.is_attr:
                    continue
                if rec.barcode and not new_barcode:
                    raise ValidationError(_('Không được để trống mã vạch'))

        res = super(ProductTemplate, self).write(vals)

        for rec in self:
            if rec.is_attr and rec.barcode:
                rec.barcode = False

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

    @api.onchange('categ_id')
    def _onchange_categ_id_clear_barcode_when_has_attr(self):
        for rec in self:
            if rec.categ_id and rec.categ_id.attr_ids:
                rec.barcode = False

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

            if rec.is_attr:
                for variant in variants:
                    if variant.barcode:
                        continue

                    barcode = rec._generate_barcode()
                    if barcode:
                        variant.barcode = barcode
                continue
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
            if rec.is_attr:
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

    @api.constrains('barcode', 'is_attr')
    def _check_template_barcode_when_has_attr(self):
        for rec in self:
            barcode = (rec.barcode or '').strip()
            if rec.is_attr and barcode:
                raise ValidationError(_(
                    'Danh mục có cấu hình thuộc tính thì không được nhập barcode ở sản phẩm cha. '
                    'Vui lòng khai báo barcode ở cấp biến thể.'
                ))

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

    @api.depends(
        'product_variant_ids',
        'product_variant_ids.default_code',
        'attribute_line_ids',
        'attribute_line_ids.value_ids',
        'attribute_line_ids.attribute_id',
        'attribute_line_ids.attribute_id.is_degree',
        'attribute_line_ids.attribute_id.symbol_degree',
    )
    def _compute_default_code(self):
        super()._compute_default_code()

        for rec in self:
            if not rec.product_variant_ids:
                rec.default_code = False
                continue

            if rec.attribute_line_ids:
                code = rec._build_default_code_from_attributes()
                if code:
                    rec.default_code = code

    def _build_default_code_from_attributes(self):
        self.ensure_one()

        degree_parts = []
        normal_parts = []

        for line in self.attribute_line_ids.sorted(lambda l: l.sequence):
            attribute = line.attribute_id
            if not line.value_ids:
                continue

            values = line.value_ids.sorted(lambda v: v.sequence)

            for value in values:
                text = value.name or ''
                if not text:
                    continue

                if attribute and attribute.is_degree:
                    symbol = attribute.symbol_degree or ''
                    text = f'{symbol}{text}' if symbol else text
                    degree_parts.append(text)
                else:
                    normal_parts.append(text)

        result_parts = []

        if degree_parts:
            result_parts.append(f"({', '.join(degree_parts)})")

        if normal_parts:
            result_parts.append(' '.join(normal_parts))

        return ' '.join(result_parts) if result_parts else False

    @api.constrains('default_code')
    def _check_unique_default_code(self):
        for rec in self:
            default_code = (rec.default_code or '').strip()
            if not default_code:
                continue

            duplicate = self.search([
                ('id', '!=', rec.id),
                ('default_code', '=', default_code),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    _('Mã tham chiếu "%s" đã tồn tại ở sản phẩm "%s".') % (default_code, duplicate.display_name))
