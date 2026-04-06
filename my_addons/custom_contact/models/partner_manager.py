from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PartnerManager(models.Model):
    _name = "partner.manager"
    _description = "Quản lý đối tác"

    partner_id = fields.Many2one(comodel_name="res.partner", string="Đối tác", ondelete="cascade")
    x_customer_tier_id = fields.Many2one(comodel_name="agent.tier", string="Hạng khách hàng", required=True)
    x_salesperson_id = fields.Many2one(comodel_name="hr.employee", string="Nhân viên phụ trách chính", required=True)
    x_salesperson_ids = fields.Many2many(comodel_name="hr.employee", relation="partner_manager_hr_employee_rel",
                                         column1="partner_manager_id", column2="employee_id", string="Nhân viên hỗ trợ")
