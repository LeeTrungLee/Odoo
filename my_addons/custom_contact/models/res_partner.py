from odoo import api, models, fields
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
    x_contact_code = fields.Char(string="Mã đối tác", copy=False, index=True, tracking=True)
    x_is_internal = fields.Boolean(string="Đối tượng nội bộ")
    partner_manager_ids = fields.One2many(comodel_name="partner.manager", inverse_name="partner_id",
                                          string="Quản lý đối tác")
    partner_dept_ids = fields.One2many(comodel_name="debt.partner", inverse_name="partner_id", string="Quản lý công nợ")

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
            if not rec.email:
                continue
            email = rec.email.strip()
            if " " in email:
                raise ValidationError("Email không được chứa khoảng trắng")

            if email.count('@') != 1:
                raise ValidationError("Email chỉ được chứa duy nhất 1 ký tự '@'.")
            local_part, domain_part = email.split('@')

            if not local_part:
                raise ValidationError("Email phải có ít nhất 1 ký tự đứng trước '@'")

            if "." not in domain_part:
                raise ValidationError("Phần sau '@' phải có tối thiểu 1 dấu chấm (.)")

            duplicate = self.sudo().search([("email", "=", email), ('id', '!=', rec.id)], limit=1)
            if duplicate:
                raise ValidationError("Email đã tồn tại trên hệ thống")

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
                raise ValidationError("Số điện thoại là bắt buộc")

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

            if identification_number.isdigit():
                raise ValidationError("Số CCCD chỉ được chứa chữ số")

            if identification_number:
                if len(identification_number) < 12:
                    raise ValidationError("Số CCCD không nhập ít hơn 12 ký tự")

                duplicate_id = self.sudo().search(
                    [("x_identification_number", "=", identification_number), ('id', '!=', rec.id)], limit=1)
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

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            vat = (val.get("vat") or "").strip()
            phone = self._normalize_phone_for_contact_code(val.get("phone"))

            if vat:
                val["x_contact_code"] = vat
            elif phone:
                val["x_contact_code"] = phone
            elif not val.get("x_contact_code"):
                val["x_contact_code"] = self._generate_contact_code()
        return super().create(vals)

    def write(self, vals):
        result = True
        driver_fields = {"vat", "phone"}
        touch_driver_fields = any(field in vals for field in driver_fields)
        user_updates_contact_code = "x_contact_code" in vals

        for rec in self:
            write_vals = dict(vals)

            if not user_updates_contact_code and touch_driver_fields:
                new_priority_code = rec._get_contact_code_by_priority(vals)

                if new_priority_code:
                    current_code = (rec.x_contact_code or "").strip()
                    old_priority_code = rec._get_contact_code_by_priority()

                    if (
                            not current_code
                            or self._is_system_generated_contact_code(current_code)
                            or current_code == old_priority_code
                    ):
                        write_vals["x_contact_code"] = new_priority_code

            result = result and super(ResPartner, rec).write(write_vals)
        return result

    @api.onchange('vat')
    def _onchange_vat(self):
        for rec in self:
            vat = (rec.vat or '').strip().upper()

            if not vat:
                rec.name = False
                rec.street = False
                rec.city = False
                rec.state_id = False
                rec.country_id = False
                return

            try:
                response = requests.get(
                    'https://mst.minvoice.com.vn/api/System/SearchTaxCodeV2',
                    params={'tax': vat},
                    timeout=10,
                )
                response.raise_for_status()
                data = response.json() or {}
            except Exception:
                raise UserError('Không gọi được API tra cứu mã số thuế.')

            api_vat = (data.get('ma_so_thue') or data.get('masothue_id') or '').strip().upper()

            if not data or api_vat != vat:
                rec.name = False
                rec.street = False
                rec.city = False
                rec.state_id = False
                rec.country_id = False
                raise ValidationError("Mã số thuế không chính xác")

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

                    country = self.env['res.country'].sudo().search([
                        '|',
                        ('name', 'ilike', country_name),
                        ('code', '=',
                         'VN' if country_name.lower() in ['việt nam', 'viet nam'] else country_name.upper())
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
