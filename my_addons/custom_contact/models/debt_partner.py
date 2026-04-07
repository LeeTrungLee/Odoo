from odoo import api, fields, models

class DebtPartner(models.Model):
    _name = 'debt.partner'
    _description = 'Công nợ'

    partner_id = fields.Many2one(comodel_name="res.partner", string="Công nợ", ondelete="cascade")
    x_credit_limit = fields.Integer(string="Hạn mức công nợ")
    x_credit_used = fields.Char(string="Công nợ hiện tại")
    x_credit_available = fields.Char(string="Hạn mức còn lại")
    x_credit_overdue = fields.Char(string="Công nợ quá hạn")
