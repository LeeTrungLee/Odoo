from odoo import api, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _update_internal_partner(self):
        for employee in self:
            partners = self.env["res.partner"].browse()

            if employee.work_contact_id:
                partners |= employee.work_contact_id

            if employee.user_id and employee.user_id.partner_id:
                partners |= employee.user_id.partner_id

            if partners:
                vals = {
                    "x_is_internal": True,
                    "x_partner_type": "employee",
                }

                if "work_phone" in employee._fields and employee.work_phone:
                    vals["phone"] = employee.work_phone

                partners.sudo().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees._update_internal_partner()
        return employees

    def write(self, vals):
        res = super().write(vals)
        self._update_internal_partner()
        return res