from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AgentTier(models.Model):
    _name = 'agent.tier'
    _description = 'Hạng khách hàng'
    _rec_name = 'name'

    name = fields.Char(string='Tên hạng đại lý', required=True)
    code = fields.Char(string='Mã hạng', required=True)
    sequence = fields.Integer(string='Thứ tự')
    description = fields.Text(string='Mô tả')
    min_sales_amount = fields.Monetary(string='Doanh số tối thiểu')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id,
                                  required=True)
    active = fields.Boolean(default=True)
    partner_count = fields.Integer(string='Số khách thuộc hạng', compute='_compute_partner_count')

    _code_unique = models.Constraint(
        "UNIQUE(code)",
        "Mã hạng phải là duy nhất.",
    )

    def _compute_partner_count(self):
        grouped_data = self.env['res.partner'].read_group(
            domain=[('x_customer_tier_id', 'in', self.ids)],
            fields=['x_customer_tier_id'],
            groupby=['x_customer_tier_id'],
        )

        count_map = {
            item['x_customer_tier_id'][0]: item['x_customer_tier_id_count']
            for item in grouped_data
            if item.get('x_customer_tier_id')
        }

        for rec in self:
            rec.partner_count = count_map.get(rec.id, 0)

    @api.constrains('sequence')
    def _check_duplicate_sequence(self):
        for rec in self:
            if not rec.sequence:
                continue

            duplicate = self.search([('id', '!=', rec.id), ('sequence', '=', rec.sequence)], limit=1)

            if duplicate:
                raise ValidationError(_("Thứ tự hạng không được trùng. Giá trị '%s' đã tồn tại.") % rec.sequence)

    @api.constrains('currency_id', 'min_sales_amount')
    def _check_duplicate_min_sales_amount(self):
        for rec in self:
            if not rec.currency_id:
                continue

            duplicate = self.search([('id', '!=', rec.id), ('currency_id', '=', rec.currency_id.id),
                                     ('min_sales_amount', '=', rec.min_sales_amount)], limit=1)

            if duplicate:
                raise ValidationError(_("Trong cùng một đơn vị tiền tệ, doanh số tối thiểu không được trùng nhau."))
