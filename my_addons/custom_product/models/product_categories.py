from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    barcode_prefix = fields.Char(string='Barcode Prefix', required=True, size=5)
    attr_ids = fields.One2many(comodel_name='product.category.config.atr', inverse_name='category_id',
                               string='Cấu hình thuộc tính')

    @api.constrains('barcode_prefix')
    def _check_barcode_prefix(self):
        for rec in self:
            value = (rec.barcode_prefix or '').strip()
            if not value:
                continue
            if not value.isdigit():
                raise ValidationError(_('Barcode Prefix chỉ được chứa số.'))
            if len(value) != 5:
                raise ValidationError(_('Barcode Prefix phải đúng 5 ký tự.'))


class ProductCategoryConfigAtr(models.Model):
    _name = 'product.category.config.atr'
    _description = 'Cấu hình thuộc tính'
    _order = 'sequence asc'

    category_id = fields.Many2one(comodel_name='product.category', string="Danh mục")
    sequence = fields.Integer(string='Thứ tự')
    attribute_id = fields.Many2one(comodel_name='product.attribute', string='Thuộc tính')

    @api.constrains('sequence', 'attribute_id', 'category_id')
    def _check_sequence(self):
        for rec in self:
            if rec.sequence in (False, None) and not rec.attribute_id:
                continue

            if rec.sequence not in (False, None) and not rec.attribute_id:
                raise ValidationError('Phải chọn Thuộc tính khi đã nhập Thứ tự!')

            if rec.attribute_id and rec.sequence in (False, None):
                raise ValidationError('Phải nhập Thứ tự khi đã chọn Thuộc tính!')

            if rec.sequence is not None and rec.sequence <= 0:
                raise ValidationError('Thứ tự phải là số nguyên dương!')

    @api.constrains('sequence', 'category_id')
    def _check_unique_sequence_per_category(self):
        for rec in self:
            if not rec.category_id:
                continue

            duplicate = self.search([
                ('id', '!=', rec.id),
                ('category_id', '=', rec.category_id.id),
                ('sequence', '=', rec.sequence),
            ], limit=1)

            if duplicate:
                raise ValidationError('Thứ tự không được trùng trong cùng một danh mục!')

    @api.constrains('attribute_id', 'category_id')
    def _check_unique_attribute_per_category(self):
        for rec in self:
            if not rec.category_id or not rec.attribute_id:
                continue

            duplicate = self.search([
                ('id', '!=', rec.id),
                ('category_id', '=', rec.category_id.id),
                ('attribute_id', '=', rec.attribute_id.id),
            ], limit=1)

            if duplicate:
                raise ValidationError(_('Không được chọn cùng Thuộc tính trong cùng một Danh mục!'))
