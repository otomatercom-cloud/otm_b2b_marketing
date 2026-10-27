# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..models.otm_b2b_day_trip import KM_RATE_PARAM


class OtmB2bDayTripStartWizard(models.TransientModel):
    """Start the day from home: enter the starting meter reading."""
    _name = 'otm.b2b.day.trip.start.wizard'
    _description = 'Start Day Trip'

    start_meter = fields.Float(string='Start Meter Reading', digits=(12, 1), required=True)
    notes = fields.Char(string='Notes')
    rate_per_km = fields.Float(string='Rate per KM', digits=(16, 2), readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Odometer continues from where the last completed trip ended.
        last = self.env['otm.b2b.day.trip'].search(
            [('user_id', '=', self.env.uid), ('state', '!=', 'in_progress')], order='trip_date desc, id desc', limit=1)
        if last and 'start_meter' in fields_list:
            res['start_meter'] = last.end_meter
        res['rate_per_km'] = float(self.env['ir.config_parameter'].sudo().get_param(KM_RATE_PARAM, '0') or 0)
        return res

    def action_start(self):
        self.ensure_one()
        Trip = self.env['otm.b2b.day.trip']
        if Trip.search_count([('user_id', '=', self.env.uid), ('state', '=', 'in_progress')]):
            raise UserError(_('You already have a trip in progress. Complete it first.'))
        trip = Trip.create({
            'user_id': self.env.uid,
            'start_meter': self.start_meter,
            'notes': self.notes,
            'rate_per_km': self.rate_per_km,
        })
        return {
            'type': 'ir.actions.act_window', 'res_model': 'otm.b2b.day.trip',
            'view_mode': 'form', 'res_id': trip.id,
        }


class OtmB2bDayTripStopWizard(models.TransientModel):
    """Reached a place: enter the meter reading there, or the km directly."""
    _name = 'otm.b2b.day.trip.stop.wizard'
    _description = 'Add Trip Stop'

    trip_id = fields.Many2one('otm.b2b.day.trip', required=True, readonly=True)
    last_meter = fields.Float(string='Last Meter Reading', digits=(12, 1), readonly=True)
    line_type = fields.Selection([('visit', 'Institution Visit'), ('other', 'Other Stop')],
                                 string='Stop Type', default='visit', required=True)
    visit_plan_id = fields.Many2one('otm.b2b.visit.plan', string="Today's Visit Plan")
    institution_id = fields.Many2one('otm.b2b.institution', string='Institution')
    location_name = fields.Char(string='Location')
    entry_mode = fields.Selection([('meter', 'Meter Reading'), ('km', 'Enter KM')],
                                  string='Entry', default='meter', required=True)
    meter_reading = fields.Float(string='Meter Reading', digits=(12, 1))
    manual_km = fields.Float(string='KM Travelled', digits=(12, 1))

    @api.onchange('trip_id')
    def _onchange_trip_id(self):
        self.last_meter = self.trip_id.end_meter

    @api.onchange('visit_plan_id')
    def _onchange_visit_plan_id(self):
        if self.visit_plan_id:
            self.institution_id = self.visit_plan_id.institution_id
            self.location_name = self.visit_plan_id.institution_id.name

    @api.onchange('institution_id')
    def _onchange_institution_id(self):
        if self.institution_id and not self.location_name:
            self.location_name = self.institution_id.name

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        trip = self.env['otm.b2b.day.trip'].browse(res.get('trip_id') or self.env.context.get('default_trip_id'))
        if trip:
            res['last_meter'] = trip.end_meter
        return res

    def action_add(self):
        self.ensure_one()
        trip = self.trip_id
        if trip.state != 'in_progress':
            raise UserError(_('This trip is not in progress.'))
        if not (self.location_name or self.institution_id):
            raise UserError(_('Enter the location or choose an institution.'))
        if self.entry_mode == 'meter' and self.meter_reading < trip.end_meter:
            raise UserError(_('Meter reading cannot be lower than the last reading (%.1f).') % trip.end_meter)
        if self.entry_mode == 'km' and self.manual_km <= 0:
            raise UserError(_('Enter the km travelled.'))
        trip._add_line({
            'line_type': self.line_type,
            'institution_id': self.institution_id.id,
            'visit_plan_id': self.visit_plan_id.id,
            'location_name': self.location_name,
            'entry_mode': self.entry_mode,
            'meter_reading': self.meter_reading,
            'manual_km': self.manual_km,
        })
        return {'type': 'ir.actions.act_window_close'}


class OtmB2bDayTripFinishWizard(models.TransientModel):
    """Reached home: final meter reading (or km), completes the day."""
    _name = 'otm.b2b.day.trip.finish.wizard'
    _description = 'Return Home & Complete Day'

    trip_id = fields.Many2one('otm.b2b.day.trip', required=True, readonly=True)
    last_meter = fields.Float(string='Last Meter Reading', digits=(12, 1), readonly=True)
    entry_mode = fields.Selection([('meter', 'Meter Reading'), ('km', 'Enter KM')],
                                  string='Entry', default='meter', required=True)
    meter_reading = fields.Float(string='Meter Reading at Home', digits=(12, 1))
    manual_km = fields.Float(string='KM Travelled (last leg)', digits=(12, 1))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        trip = self.env['otm.b2b.day.trip'].browse(res.get('trip_id') or self.env.context.get('default_trip_id'))
        if trip:
            res['last_meter'] = trip.end_meter
        return res

    def action_finish(self):
        self.ensure_one()
        trip = self.trip_id
        if trip.state != 'in_progress':
            raise UserError(_('This trip is not in progress.'))
        if self.entry_mode == 'meter' and self.meter_reading < trip.end_meter:
            raise UserError(_('Meter reading cannot be lower than the last reading (%.1f).') % trip.end_meter)
        if self.entry_mode == 'km' and self.manual_km < 0:
            raise UserError(_('KM cannot be negative.'))
        trip._finish({
            'entry_mode': self.entry_mode,
            'meter_reading': self.meter_reading,
            'manual_km': self.manual_km,
        })
        return {
            'type': 'ir.actions.act_window', 'res_model': 'otm.b2b.day.trip',
            'view_mode': 'form', 'res_id': trip.id,
        }


class OtmB2bTravelSettingsWizard(models.TransientModel):
    """Marketing Head sets the per-km amount (small dedicated wizard rather
    than res.config.settings, see ODOO19_RULES.md on settings-view xpaths)."""
    _name = 'otm.b2b.travel.settings.wizard'
    _description = 'Travel Settings'

    rate_per_km = fields.Float(string='Amount per KM', digits=(16, 2))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['rate_per_km'] = float(self.env['ir.config_parameter'].sudo().get_param(KM_RATE_PARAM, '0') or 0)
        return res

    def action_save(self):
        self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param(KM_RATE_PARAM, str(self.rate_per_km))
        return {'type': 'ir.actions.act_window_close'}
