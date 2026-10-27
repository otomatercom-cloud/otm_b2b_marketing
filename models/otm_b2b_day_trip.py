# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

KM_RATE_PARAM = 'otm_b2b_marketing.km_rate'


class OtmB2bDayTrip(models.Model):
    """One day's travel for a Marketing Executive: starts from home with a
    meter reading, stops at each place (meter reading OR km typed in), and
    ends back home. Total km x rate-per-km = travel claim amount; stops of
    type 'Visit' give the day's visit count."""
    _name = 'otm.b2b.day.trip'
    _description = 'B2B Day Trip (KM Tracking)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'trip_date desc, id desc'

    name = fields.Char(string='Trip', compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='Marketing Executive', required=True,
                              default=lambda self: self.env.user, tracking=True, index=True)
    trip_date = fields.Date(string='Date', required=True, default=fields.Date.context_today,
                            tracking=True, index=True)
    state = fields.Selection([
        ('in_progress', 'On Trip'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
    ], string='Status', default='in_progress', required=True, tracking=True)
    start_time = fields.Datetime(string='Started At', default=fields.Datetime.now)
    end_time = fields.Datetime(string='Ended At')
    start_meter = fields.Float(string='Start Meter Reading', digits=(12, 1), required=True)
    end_meter = fields.Float(string='End Meter Reading', digits=(12, 1),
                             compute='_compute_totals', store=True)
    line_ids = fields.One2many('otm.b2b.day.trip.line', 'trip_id', string='Stops', copy=False)
    total_km = fields.Float(string='Total KM', digits=(12, 1), compute='_compute_totals', store=True)
    visit_count = fields.Integer(string='Visits', compute='_compute_totals', store=True)
    stop_count = fields.Integer(string='Stops', compute='_compute_totals', store=True)
    rate_per_km = fields.Float(
        string='Rate per KM', digits=(16, 2), tracking=True,
        default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param(KM_RATE_PARAM, '0') or 0),
        help='Copied from Travel Settings when the trip starts, so later rate changes '
             'never alter past trips.')
    amount = fields.Monetary(string='Travel Amount', compute='_compute_totals', store=True,
                             currency_field='currency_id')
    notes = fields.Text(string='Notes')
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Currency')
    access_token = fields.Char(copy=False, readonly=True, default=lambda self: uuid.uuid4().hex)
    portal_url = fields.Char(string='Mobile Link', compute='_compute_portal_url')

    @api.depends('user_id', 'trip_date')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.user_id.name or '', rec.trip_date or '')

    def _compute_portal_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.portal_url = (
                f"{base_url}/b2b/trip/{rec.id}/{rec.access_token}"
                if isinstance(rec.id, int) and rec.access_token else False)

    @api.depends('start_meter', 'rate_per_km', 'line_ids.km', 'line_ids.meter_after', 'line_ids.line_type',
                 'line_ids.sequence')
    def _compute_totals(self):
        for rec in self:
            lines = rec.line_ids.sorted(key=lambda l: (l.sequence, l.id))
            rec.total_km = sum(lines.mapped('km'))
            rec.end_meter = lines[-1].meter_after if lines else rec.start_meter
            rec.visit_count = len(lines.filtered(lambda l: l.line_type == 'visit'))
            rec.stop_count = len(lines)
            rec.amount = rec.total_km * rec.rate_per_km

    @api.constrains('user_id', 'state')
    def _check_single_open_trip(self):
        for rec in self.filtered(lambda r: r.state == 'in_progress'):
            other = self.search_count([
                ('id', '!=', rec.id), ('user_id', '=', rec.user_id.id), ('state', '=', 'in_progress')])
            if other:
                raise ValidationError(_(
                    '%s already has a trip in progress. Complete it before starting a new one.',
                    rec.user_id.name))

    def write(self, vals):
        if vals.get('state') == 'approved' and not self.env.user.has_group(
                'otm_b2b_marketing.group_otm_b2b_marketing_manager'):
            raise ValidationError(_('Only a Marketing Manager can approve trips.'))
        return super().write(vals)

    def action_approve(self):
        for rec in self:
            if rec.state != 'completed':
                raise ValidationError(_('Only completed trips can be approved.'))
        self.write({'state': 'approved', 'approved_by_id': self.env.uid})

    def action_reopen(self):
        self.write({'state': 'in_progress', 'end_time': False, 'approved_by_id': False})

    def action_open_add_stop(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Add Stop'),
            'res_model': 'otm.b2b.day.trip.stop.wizard', 'view_mode': 'form', 'target': 'new',
            'context': {'default_trip_id': self.id},
        }

    def action_open_finish(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Return Home & Complete Day'),
            'res_model': 'otm.b2b.day.trip.finish.wizard', 'view_mode': 'form', 'target': 'new',
            'context': {'default_trip_id': self.id},
        }

    def _add_line(self, vals):
        """Append a stop after the current last one."""
        self.ensure_one()
        last = self.line_ids.sorted(key=lambda l: (l.sequence, l.id))[-1:]
        vals = dict(vals, trip_id=self.id, sequence=(last.sequence + 10) if last else 10)
        return self.env['otm.b2b.day.trip.line'].create(vals)

    def _finish(self, vals):
        self.ensure_one()
        vals = dict(vals, line_type='home', location_name=vals.get('location_name') or _('Home'))
        self._add_line(vals)
        self.write({'state': 'completed', 'end_time': fields.Datetime.now()})
        self.message_post(body=_('Day completed: %(km).1f km, %(visits)s visits, amount %(amt).2f',
                                 km=self.total_km, visits=self.visit_count, amt=self.amount))


class OtmB2bDayTripLine(models.Model):
    _name = 'otm.b2b.day.trip.line'
    _description = 'B2B Day Trip Stop'
    _order = 'trip_id, sequence, id'

    trip_id = fields.Many2one('otm.b2b.day.trip', string='Trip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Seq', default=10)
    line_type = fields.Selection([
        ('visit', 'Institution Visit'),
        ('other', 'Other Stop'),
        ('home', 'Home (End)'),
    ], string='Type', default='visit', required=True)
    institution_id = fields.Many2one('otm.b2b.institution', string='Institution')
    visit_plan_id = fields.Many2one('otm.b2b.visit.plan', string='Visit Plan')
    location_name = fields.Char(string='Location')
    time = fields.Datetime(string='Reached At', default=fields.Datetime.now)
    entry_mode = fields.Selection([
        ('meter', 'Meter Reading'),
        ('km', 'Enter KM'),
    ], string='Entry', default='meter', required=True)
    meter_reading = fields.Float(string='Meter Reading', digits=(12, 1))
    manual_km = fields.Float(string='KM Entered', digits=(12, 1))
    km = fields.Float(string='KM (from previous)', digits=(12, 1), compute='_compute_km', store=True)
    meter_after = fields.Float(string='Meter After', digits=(12, 1), compute='_compute_km', store=True)
    user_id = fields.Many2one(related='trip_id.user_id', store=True, string='Executive')
    trip_date = fields.Date(related='trip_id.trip_date', store=True)

    @api.depends('entry_mode', 'meter_reading', 'manual_km', 'sequence',
                 'trip_id.start_meter', 'trip_id.line_ids.entry_mode', 'trip_id.line_ids.meter_reading',
                 'trip_id.line_ids.manual_km', 'trip_id.line_ids.sequence')
    def _compute_km(self):
        cache = {}
        for line in self:
            trip = line.trip_id
            if not trip:
                line.km = line.meter_after = 0.0
                continue
            if trip not in cache:
                running, result = trip.start_meter, {}
                for l in trip.line_ids.sorted(key=lambda r: r.sequence):
                    if l.entry_mode == 'meter':
                        km = l.meter_reading - running
                        running = l.meter_reading
                    else:
                        km = l.manual_km
                        running += km
                    result[l.id] = (km, running)
                cache[trip] = result
            line.km, line.meter_after = cache[trip].get(line.id, (0.0, 0.0))

    @api.constrains('km', 'entry_mode')
    def _check_km(self):
        for line in self:
            if line.km < 0:
                raise ValidationError(_(
                    'Stop "%(loc)s": the meter reading is lower than the previous reading '
                    '(%(prev).1f). Please check the reading.',
                    loc=line.location_name or line.institution_id.name or '',
                    prev=line.meter_after - line.km))

    def _check_trip_open(self):
        if self.env.su or self.env.user.has_group('otm_b2b_marketing.group_otm_b2b_marketing_manager'):
            return
        if self.mapped('trip_id').filtered(lambda t: t.state != 'in_progress'):
            raise ValidationError(_('Stops can only be changed while the trip is in progress.'))

    def write(self, vals):
        self._check_trip_open()
        return super().write(vals)

    def unlink(self):
        self._check_trip_open()
        return super().unlink()

    @api.onchange('institution_id')
    def _onchange_institution_id(self):
        if self.institution_id and not self.location_name:
            self.location_name = self.institution_id.name

    @api.onchange('visit_plan_id')
    def _onchange_visit_plan_id(self):
        if self.visit_plan_id:
            self.institution_id = self.visit_plan_id.institution_id
            self.location_name = self.visit_plan_id.institution_id.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('location_name') and vals.get('institution_id'):
                vals['location_name'] = self.env['otm.b2b.institution'].browse(vals['institution_id']).name
            if vals.get('visit_plan_id') and not vals.get('institution_id'):
                plan = self.env['otm.b2b.visit.plan'].browse(vals['visit_plan_id'])
                vals['institution_id'] = plan.institution_id.id
        return super().create(vals_list)
