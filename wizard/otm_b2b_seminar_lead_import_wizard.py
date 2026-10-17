# -*- coding: utf-8 -*-
import base64
import io
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

MAX_ROWS = 5000

# header text (lower-cased, spaces/punctuation stripped) -> lead field
HEADER_ALIASES = {
    'name': 'name', 'studentname': 'name', 'fullname': 'name', 'student': 'name',
    'mobile': 'mobile', 'mobileno': 'mobile', 'mobilenumber': 'mobile', 'phone': 'mobile',
    'phoneno': 'mobile', 'phonenumber': 'mobile', 'contact': 'mobile', 'contactnumber': 'mobile',
    'whatsapp': 'mobile', 'whatsappnumber': 'mobile',
    'email': 'email', 'emailid': 'email', 'emailaddress': 'email',
    'course': 'course_interested', 'courseinterested': 'course_interested',
    'interestedcourse': 'course_interested', 'coursename': 'course_interested',
    'class': 'current_class', 'currentclass': 'current_class', 'standard': 'current_class',
    'year': 'current_class', 'studying': 'current_class',
    'stream': 'stream', 'group': 'stream',
    'sourcecampaign': 'source_campaign', 'campaign': 'source_campaign',
}


def _clean_cell(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # Excel stores 9876543210 as 9876543210.0
    return str(value).strip()


def _clean_mobile(value):
    text = _clean_cell(value)
    digits = re.sub(r'\D', '', text)
    if len(digits) > 10 and digits.startswith('91'):
        digits = digits[-10:]
    return digits or text


class OtmB2bSeminarLeadImportWizard(models.TransientModel):
    """Upload the student details collected on hardcopy forms at a seminar
    (typed into the Excel template) as leads linked to that seminar."""
    _name = 'otm.b2b.seminar.lead.import.wizard'
    _description = 'Upload Seminar Students (Excel)'

    seminar_id = fields.Many2one('otm.b2b.seminar', string='Seminar', required=True, readonly=True)
    institution_id = fields.Many2one(related='seminar_id.institution_id', readonly=True)
    file = fields.Binary(string='Excel File (.xlsx)', required=True)
    filename = fields.Char(string='File Name')
    skip_duplicates = fields.Boolean(
        string='Skip students already collected for this seminar', default=True,
        help='A row is a duplicate when the same mobile number already exists on this seminar.')
    template_url = fields.Char(compute='_compute_template_url')

    def _compute_template_url(self):
        for rec in self:
            rec.template_url = '/b2b/seminar/lead_template.xlsx'

    def action_import(self):
        self.ensure_one()
        try:
            import openpyxl
        except ImportError:
            raise UserError(_('The python library "openpyxl" is not installed on the server.'))
        if self.filename and not self.filename.lower().endswith(('.xlsx', '.xlsm')):
            raise UserError(_('Please upload an .xlsx file (use "Download Template" for the format).'))
        try:
            workbook = openpyxl.load_workbook(
                io.BytesIO(base64.b64decode(self.file)), read_only=True, data_only=True)
        except Exception:
            raise UserError(_('Could not read this file. Please upload a valid .xlsx file.'))
        sheet = workbook.worksheets[0]
        rows = sheet.iter_rows(values_only=True)
        header = next(rows, None)
        if not header:
            raise UserError(_('The file is empty.'))
        columns = {}
        for idx, title in enumerate(header):
            key = re.sub(r'[^a-z]', '', _clean_cell(title).lower())
            field = HEADER_ALIASES.get(key)
            if field and field not in columns.values():
                columns[idx] = field
        if 'name' not in columns.values():
            raise UserError(_('No "Name" column found in the first row. Use the template headers: '
                              'Name, Mobile, Email, Course Interested, Current Class, Stream, Source Campaign.'))

        seminar = self.seminar_id
        Lead = self.env['otm.b2b.lead']
        seen = set()
        if self.skip_duplicates:
            seen = {m for m in seminar.lead_ids.mapped('mobile') if m}
        Stream = self.env['otm.b2b.stream'].sudo()
        stream_cache = {s.name.strip().lower(): s.id for s in Stream.search([])}
        vals_list, skipped_dup, skipped_empty = [], 0, 0
        for count, row in enumerate(rows, start=1):
            if count > MAX_ROWS:
                raise UserError(_('Too many rows (limit %s per upload). Please split the file.') % MAX_ROWS)
            data = {}
            for idx, field in columns.items():
                if idx < len(row):
                    data[field] = _clean_mobile(row[idx]) if field == 'mobile' else _clean_cell(row[idx])
            if not data.get('name'):
                skipped_empty += 1
                continue
            mobile = data.get('mobile')
            if self.skip_duplicates and mobile:
                if mobile in seen:
                    skipped_dup += 1
                    continue
                seen.add(mobile)
            stream_name = data.pop('stream', '')
            if stream_name:
                key = stream_name.lower()
                if key not in stream_cache:
                    stream_cache[key] = Stream.create({'name': stream_name}).id
                data['stream_id'] = stream_cache[key]
            data.update({
                'institution_id': seminar.institution_id.id,
                'seminar_id': seminar.id,
                'source': 'seminar',
                'entry_mode': 'excel',
                'company_id': seminar.company_id.id,
            })
            vals_list.append(data)
        leads = Lead.create(vals_list) if vals_list else Lead
        message = _('%(created)s students added, %(dup)s duplicates skipped, %(empty)s blank rows ignored.',
                    created=len(leads), dup=skipped_dup, empty=skipped_empty)
        seminar.message_post(body=message)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Upload complete'),
                'message': message,
                'type': 'success' if leads else 'warning',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
