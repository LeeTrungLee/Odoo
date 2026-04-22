from odoo import models, fields, api

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    is_degree = fields.Boolean(string='Là thuộc tính độ', default=False)
    symbol_degree = fields.Char(string='Ký hiệu', required=True)
