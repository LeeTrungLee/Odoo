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
        Partner = self.env['res.partner'].sudo()
        for rec in self:
            rec.partner_count = Partner.search_count([
                ('x_customer_tier_id', '=', rec.id),
                ('x_partner_type', '=', 'partner'),
            ])

    def write(self, vals):
        tiers_to_archive = self.env['agent.tier']
        partners_to_recompute = self.env['res.partner']

        if 'active' in vals and vals.get('active') is False:
            tiers_to_archive = self.filtered('active')

            if tiers_to_archive:
                partners_to_recompute = self.env['res.partner'].sudo().search([
                    ('x_customer_tier_id', 'in', tiers_to_archive.ids),
                ])

        if 'active' in vals and vals.get('active') is True:
            tiers_to_unarchive = self.filtered(lambda t: not t.active)
            if tiers_to_unarchive:
                for tier in tiers_to_unarchive:
                    partners_to_recompute |= self.env['res.partner'].sudo().search([
                        ('x_partner_type', '=', 'partner'),
                        ('x_total_sales_amount', '>=', tier.min_sales_amount),
                    ])

        res = super().write(vals)

        if partners_to_recompute:
            partners_to_recompute.mapped('commercial_partner_id')._update_customer_tier()

        return res

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
