from odoo import api, fields, models

class AgentTier(models.Model):
    _name = 'agent.tier'
    _description = 'Hạng khách hàng'
    _rec_name = 'name'

    name = fields.Char(string='Tên hạng đại lý', required=True)
    code = fields.Char(string='Mã hạng', required=True)
    sequence = fields.Integer(string='Thứ tự')
    description = fields.Text(string='Mô tả')
    min_sales_amount = fields.Monetary(string='Doanh số tối thiểu')
    currency_id = fields.Many2one( 'res.currency', string='Tiền tệ')
    active = fields.Boolean(default=True)
    partner_count = fields.Integer(string='Số khách thuộc hạng')

    _code_unique = models.Constraint(
        "UNIQUE(code)",
        "Mã hạng phải là duy nhất.",
    )