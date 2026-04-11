from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _prepare_internal_partner_vals(self, vals=None):
        vals = vals or {}
        partner_vals = {
            "x_is_internal": True,
            "x_partner_type": "employee",
        }

        if "phone" in vals:
            partner_vals["phone"] = vals.get("phone") or False

        if "email" in vals:
            partner_vals["email"] = (vals.get("email") or "").strip() or False

        return partner_vals

    def _update_internal_partner(self, vals=None):
        for user in self:
            if not user.partner_id:
                continue

            partner_vals = self._prepare_internal_partner_vals(vals)

            # Nếu create/write không truyền phone/email thì lấy từ user hiện tại
            if "phone" not in partner_vals and "phone" in user._fields:
                partner_vals["phone"] = user.phone or False

            if "email" not in partner_vals and "email" in user._fields:
                partner_vals["email"] = (user.email or "").strip() or False

            user.partner_id.sudo().write(partner_vals)

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user, vals in zip(users, vals_list):
            user._update_internal_partner(vals)
        return users

    def write(self, vals):
        res = super().write(vals)
        self._update_internal_partner(vals)
        return res
