from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _update_internal_partner(self):
        for user in self:
            if user.partner_id:
                vals = {
                    "x_is_internal": True,
                    "x_partner_type": "employee",
                }

                if "phone" in user._fields and user.phone:
                    vals["phone"] = user.phone

                elif "login" in user._fields and user.login:
                    vals["email"] = user.login

                user.partner_id.sudo().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._update_internal_partner()
        return users

    def write(self, vals):
        res = super().write(vals)
        self._update_internal_partner()
        return res