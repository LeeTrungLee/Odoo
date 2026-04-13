from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
import re
import requests


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_birthday = fields.Date(string="Ngày sinh")
    x_identification_number = fields.Char(string="Số CCCD")
    x_partner_type = fields.Selection([
        ('partner', 'Khách hàng'),
        ('supplier', 'Nhà cung cấp'),
        ('employee', 'Nhân viên'),
        ('other', 'Đối tác khác')
    ], string="Loại đối tác", required=True, default='partner')
    x_partner_group = fields.Selection([
        ("b2b", "B2B"),
        ("b2c", "B2C")
    ], string="Nhóm khách hàng", required=True, default='b2b')
    x_supplier_group = fields.Selection([
        ("trong", "Tròng"),
        ("gong", "Gọng"),
        ("phu_kien", "Phụ kiện"),
        ("khac", "Khác")
    ], string="Nhóm nhà cung cấp", required=True, default='gong')
    x_region = fields.Char("Khu vực", compute='_compute_region', readonly=True, store=True)
    x_contact_code = fields.Char(
        string="Mã đối tác",
        copy=False,
        index=True,
        tracking=True,
        required=True,
        compute="_compute_x_contact_code",
        inverse="_inverse_x_contact_code",
        store=True,
        precompute=True,
    )
    x_is_internal = fields.Boolean(string="Đối tượng nội bộ")

    # Hạng khách hàng
    x_customer_tier_id = fields.Many2one(comodel_name="agent.tier", string="Hạng khách hàng")
    x_salesperson_id = fields.Many2one(comodel_name="hr.employee", string="Nhân viên phụ trách chính")
    x_salesperson_ids = fields.Many2many(comodel_name="hr.employee", relation="partner_manager_hr_employee_rel",
                                         column1="partner_manager_id", column2="employee_id", string="Nhân viên hỗ trợ",
                                         domain="[('id', '!=', x_salesperson_id)]")
    x_total_sales_amount = fields.Monetary(string="Tổng doanh thu mua hàng", currency_field="company_currency_id")
    company_currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True)

    ## Công nợ
    x_credit_limit = fields.Integer(string="Hạn mức công nợ")
    x_credit_used = fields.Char(string="Công nợ hiện tại")
    x_credit_available = fields.Char(string="Hạn mức còn lại")
    x_credit_overdue = fields.Char(string="Công nợ quá hạn")

    _x_contact_code_unique = models.Constraint(
        "UNIQUE(x_contact_code)",
        "Mã đối tác phải là duy nhất.",
    )

    @api.onchange("x_partner_type")
    def _onchange_partner_type(self):
        for rec in self:
            if rec.x_partner_type == "employee":
                rec.x_is_internal = True
            else:
                rec.x_is_internal = False

    @api.constrains("vat", "is_company", "country_id", "state_id")
    def _check_validate(self):
        for rec in self:
            if rec.is_company:
                if not rec.vat:
                    raise ValidationError("Thông tin trường 'Mã số thuế' không được để trống!")
                if not rec.country_id:
                    raise ValidationError("Thông tin trường 'Quốc gia' không được để trống!")
                if not rec.state_id:
                    raise ValidationError("Thông tin trường 'Thành phố' không được để trống!")
            if rec.vat:
                duplicate_vat = self.sudo().search([("vat", "=", rec.vat), ('id', '!=', rec.id)], limit=1)
                if duplicate_vat:
                    raise ValidationError("Mã số thuế đã tồn tại trên hệ thống")

    @api.constrains("email")
    def _check_validate_email(self):
        for rec in self:
            email = (rec.email or "").strip()
            if not email:
                continue

            if any(c.isspace() for c in email):
                raise ValidationError(_("Email không được chứa khoảng trắng."))

            if email.count("@") != 1:
                raise ValidationError(_("Email phải có đúng 1 ký tự '@'."))

            local_part, domain_part = email.split("@", 1)

            if not local_part:
                raise ValidationError(_("Email phải có ít nhất 1 ký tự đứng trước '@'."))

            if "." not in domain_part:
                raise ValidationError(_("Phần sau '@' phải có tối thiểu 1 dấu chấm '.'."))

            duplicate = self.sudo().search([
                ("id", "!=", rec.id),
                ("email", "=ilike", email),
            ], limit=1)
            if duplicate:
                raise ValidationError(_("Email đã tồn tại trên hệ thống."))

    def _normalize_phone(self, phone):
        phone = (phone or "").strip()
        phone = phone.replace(" ", "")
        phone = phone.replace(".", "")
        phone = phone.replace("-", "")
        phone = phone.replace("(", "")
        phone = phone.replace(")", "")
        return phone

    @api.constrains("phone")
    def _check_validate_phone(self):
        for rec in self:
            phone = self._normalize_phone(rec.phone)

            if not phone:
                continue

            if phone.startswith("+"):
                phone_to_check = phone[1:]
            else:
                phone_to_check = phone

            if not phone_to_check.isdigit():
                raise ValidationError("Số điện thoại không hợp lệ")

            if len(phone_to_check) < 8 or len(phone_to_check) > 15:
                raise ValidationError("Số điện thoại có độ dài từ 8 đến 15 ký tự")

            if len(set(phone_to_check)) == 1:
                raise ValidationError("Số điện thoại không được là một ký tự lặp lại")

            duplicate = self.sudo().search([
                ("id", "!=", rec.id),
                ("phone", "=", rec.phone),
            ], limit=1)

            if duplicate:
                raise ValidationError("Số điện thoại không được trùng trên hệ thống")

    @api.constrains("x_identification_number")
    def _check_validate_identification_number(self):
        for rec in self:
            identification_number = (rec.x_identification_number or "").strip()

            if not identification_number:
                continue

            if " " in identification_number:
                raise ValidationError("Số CCCD không được chứa khoảng trắng")

            if not identification_number.isdigit():
                raise ValidationError("Số CCCD chỉ được chứa chữ số")

            if len(identification_number) < 12:
                raise ValidationError("Số CCCD không nhập ít hơn 12 ký tự")

            if len(identification_number) > 12:
                raise ValidationError("Số CCCD không được nhiều hơn 12 ký tự")

            duplicate_id = self.sudo().search(
                [
                    ("x_identification_number", "=", identification_number),
                    ("id", "!=", rec.id),
                ],
                limit=1,
            )
            if duplicate_id:
                raise ValidationError("Số CCCD không được trùng trên hệ thống")

    @api.depends("country_id", "state_id")
    def _compute_region(self):
        region_map = {
            "Hà Nội": "Miền Bắc",
            "Hải Phòng": "Miền Bắc",
            "Quảng Ninh": "Miền Bắc",
            "Lạng Sơn": "Miền Bắc",
            "Cao Bằng": "Miền Bắc",
            "Tuyên Quang": "Miền Bắc",
            "Lào Cai": "Miền Bắc",
            "Lai Châu": "Miền Bắc",
            "Điện Biên": "Miền Bắc",
            "Sơn La": "Miền Bắc",
            "Phú Thọ": "Miền Bắc",
            "Thái Nguyên": "Miền Bắc",
            "Bắc Ninh": "Miền Bắc",
            "Hưng Yên": "Miền Bắc",
            "Ninh Bình": "Miền Bắc",

            "Thanh Hóa": "Miền Trung",
            "Nghệ An": "Miền Trung",
            "Hà Tĩnh": "Miền Trung",
            "Quảng Trị": "Miền Trung",
            "Thừa Thiên Huế": "Miền Trung",
            "Đà Nẵng": "Miền Trung",
            "Quảng Ngãi": "Miền Trung",
            "Khánh Hòa": "Miền Trung",
            "Gia Lai": "Miền Trung",
            "Đắk Lắk": "Miền Trung",
            "Lâm Đồng": "Miền Trung",

            "TP Hồ Chí Minh": "Miền Nam",
            "Đồng Nai": "Miền Nam",
            "Tây Ninh": "Miền Nam",
            "An Giang": "Miền Nam",
            "Đồng Tháp": "Miền Nam",
            "Vĩnh Long": "Miền Nam",
            "Cần Thơ": "Miền Nam",
            "Cà Mau": "Miền Nam",
        }
        for rec in self:
            rec.x_region = False

            if rec.country_id and rec.country_id.code == "VN" and rec.state_id:
                state_name = (rec.state_id.name or "").strip()
                rec.x_region = region_map.get(state_name, False)

    def _normalize_phone_for_contact_code(self, phone):
        phone = (phone or "").strip()
        return re.sub(r"\D", "", phone)

    def _is_system_generated_contact_code(self, code):
        code = (code or "").strip()
        return bool(re.match(r"^KH\d{9}$", code))

    def _get_contact_code_by_priority(self, vals=None):
        self.ensure_one()
        vals = vals or {}

        vat = vals.get("vat", self.vat)
        phone = vals.get("phone", self.phone)

        vat = (vat or "").strip()
        phone = self._normalize_phone_for_contact_code(phone)

        if vat:
            return vat
        if phone:
            return phone
        return False

    @api.model
    def _generate_contact_code(self):
        return self.env["ir.sequence"].next_by_code("res.partner.contact.code")

    @api.depends("vat", "phone")
    def _compute_x_contact_code(self):
        for rec in self:
            vat = (rec.vat or "").strip()
            phone = rec._normalize_phone_for_contact_code(rec.phone)

            if vat:
                rec.x_contact_code = vat
            elif phone:
                rec.x_contact_code = phone
            elif not rec.x_contact_code:
                rec.x_contact_code = rec._generate_contact_code()

    def _inverse_x_contact_code(self):
        for rec in self:
            rec.x_contact_code = rec.x_contact_code

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        customer_partners = partners.filtered(lambda p: p.x_partner_type == "partner")
        customer_partners._update_customer_tier()
        return partners

    def write(self, vals):
        for rec in self:
            write_vals = dict(vals)
            if "x_partner_type" in write_vals:
                write_vals["x_is_internal"] = write_vals["x_partner_type"] == "employee"
            super(ResPartner, rec).write(write_vals)
        return True

    @api.onchange('vat')
    def _onchange_vat(self):
        for rec in self:
            if rec.is_company:
                vat = (rec.vat or '').strip()

                if not vat:
                    rec.name = False
                    rec.street = False
                    rec.city = False
                    rec.state_id = False
                    rec.country_id = False
                    continue

                try:
                    response = requests.get(
                        'https://mst.minvoice.com.vn/api/System/SearchTaxCodeV2',
                        params={'tax': vat},
                        timeout=10,
                    )
                    response.raise_for_status()
                    data = response.json() or {}
                except requests.RequestException:
                    raise UserError(_('Không gọi được API tra cứu mã số thuế.'))

                api_vat = (data.get('ma_so_thue') or data.get('masothue_id') or '').strip().upper()

                if not data or api_vat != vat:
                    raise UserError(_('Mã số thuế không chính xác.'))
                rec.name = data.get('ten_cty') or False

                full_address = (data.get('dia_chi') or '').strip()
                rec.street = False
                rec.city = False
                rec.state_id = False
                rec.country_id = False

                if full_address:
                    parts = [p.strip() for p in full_address.split(',') if p.strip()]

                    if len(parts) >= 4:
                        rec.street = ', '.join(parts[:-3])
                        rec.city = parts[-3]

                        state_name = parts[-2]
                        country_name = parts[-1]

                        for prefix in ['Tỉnh ', 'Thành phố ', 'TP. ', 'TP ']:
                            if state_name.startswith(prefix):
                                state_name = state_name.replace(prefix, '', 1).strip()
                                break

                        country_code = 'VN' if country_name.lower() in ['việt nam', 'viet nam'] else country_name.upper()
                        country = self.env['res.country'].sudo().search([
                            '|',
                            ('name', 'ilike', country_name),
                            ('code', '=', country_code)
                        ], limit=1)

                        if country:
                            rec.country_id = country.id

                        state_domain = [('name', 'ilike', state_name)]
                        if rec.country_id:
                            state_domain.append(('country_id', '=', rec.country_id.id))

                        state = self.env['res.country.state'].sudo().search(state_domain, limit=1)
                        if state:
                            rec.state_id = state.id

                    elif len(parts) == 3:
                        rec.street = parts[0]

                        state_name = parts[1]
                        country_name = parts[2]

                        for prefix in ['Tỉnh ', 'Thành phố ', 'TP. ', 'TP ']:
                            if state_name.startswith(prefix):
                                state_name = state_name.replace(prefix, '', 1).strip()
                                break

                        country_code = 'VN' if country_name.lower() in ['việt nam', 'viet nam'] else country_name.upper()

                        country = self.env['res.country'].sudo().search([
                            '|',
                            ('name', 'ilike', country_name),
                            ('code', '=', country_code)
                        ], limit=1)

                        if country:
                            rec.country_id = country.id

                        state_domain = [('name', 'ilike', state_name)]
                        if rec.country_id:
                            state_domain.append(('country_id', '=', rec.country_id.id))

                        state = self.env['res.country.state'].sudo().search(state_domain, limit=1)
                        if state:
                            rec.state_id = state.id
                    else:
                        rec.street = full_address

    @api.onchange("x_salesperson_id")
    def _onchange_x_salesperson_id(self):
        for rec in self:
            if rec.x_salesperson_id:
                rec.x_salesperson_ids = rec.x_salesperson_ids.filtered(
                    lambda emp: emp != rec.x_salesperson_id
                )

    @api.constrains("x_salesperson_id", "x_salesperson_ids")
    def _check_salesperson_not_duplicated(self):
        for rec in self:
            if rec.x_salesperson_id and rec.x_salesperson_id in rec.x_salesperson_ids:
                raise ValidationError(
                    _("Nhân viên phụ trách chính không được nằm trong danh sách nhân viên hỗ trợ.")
                )

    def _get_confirmed_sale_amount(self):
        self.ensure_one()

        commercial_partner = self.commercial_partner_id

        groups = self.env["sale.order"].sudo().read_group(
            domain=[
                ("partner_id", "child_of", commercial_partner.id),
                ("state", "=", "sale"),
            ],
            fields=["amount_total:sum"],
            groupby=[],
        )

        return groups[0].get("amount_total", 0.0) if groups else 0.0

    def _update_customer_tier(self):
        Tier = self.env["agent.tier"].sudo()

        for partner in self:
            total_amount = partner._get_confirmed_sale_amount()
            currency = partner.company_id.currency_id or self.env.company.currency_id

            tier = Tier.search(
                [
                    ("active", "=", True),
                    ("currency_id", "=", currency.id),
                    ("min_sales_amount", "<=", total_amount),
                ],
                order="min_sales_amount desc, sequence asc, id asc",
                limit=1,
            )

            partner.write({
                "x_total_sales_amount": total_amount,
                "x_customer_tier_id": tier.id if tier else False,
            })
