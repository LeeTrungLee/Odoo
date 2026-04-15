from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()
        partners = self.mapped("partner_id").mapped("commercial_partner_id")
        partners._update_customer_tier()

        return res

    def action_cancel(self):
        partners = self.mapped("partner_id").mapped("commercial_partner_id")
        res = super().action_cancel()
        partners._update_customer_tier()
        return res
