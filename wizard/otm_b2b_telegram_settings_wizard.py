# -*- coding: utf-8 -*-
import uuid
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


class OtmB2bTelegramSettingsWizard(models.TransientModel):
    """Standalone settings screen for the Telegram bot connection.
    Deliberately NOT built on res.config.settings - Rule 5 (xpath anchors
    on that view are unreliable across Odoo 19 upgrades); a small
    dedicated wizard reading/writing ir.config_parameter is simpler and
    doesn't depend on any other module's view structure."""
    _name = 'otm.b2b.telegram.settings.wizard'
    _description = 'Telegram Bot Settings'

    bot_username = fields.Char(
        string='Bot Username',
        help="Without the @ - e.g. LogicSchoolB2BBot. Used to build each officer's "
             "personal Connect Telegram link.")
    bot_token = fields.Char(
        string='Bot Token',
        help="From @BotFather on Telegram. Stored as a system parameter, never shown in views/logs.")
    reminder_hour = fields.Float(
        string="Daily Reminder Time", default=9.0, widget='float_time',
        help="What time each day the Visit Planned / Today's Visit reminders go out.")
    not_submitted_reminder_hours = fields.Float(
        string='Nudge After (Hours)', default=4.0,
        help="If an officer checks in and hasn't submitted the visit after this many hours, "
             "send a one-time reminder nudge. Checked hourly.")
    webhook_status = fields.Char(string='Webhook Status', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        params = self.env['ir.config_parameter'].sudo()
        res['bot_username'] = params.get_param('otm_b2b_marketing.telegram_bot_username', '')
        res['bot_token'] = params.get_param('otm_b2b_marketing.telegram_bot_token', '')
        res['reminder_hour'] = float(params.get_param('otm_b2b_marketing.telegram_reminder_hour', '9.0') or 9.0)
        res['not_submitted_reminder_hours'] = float(params.get_param(
            'otm_b2b_marketing.telegram_not_submitted_reminder_hours', '4.0') or 4.0)
        return res

    def action_save(self):
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('otm_b2b_marketing.telegram_bot_username', self.bot_username or '')
        params.set_param('otm_b2b_marketing.telegram_bot_token', self.bot_token or '')
        params.set_param('otm_b2b_marketing.telegram_reminder_hour', str(self.reminder_hour or 9.0))
        params.set_param(
            'otm_b2b_marketing.telegram_not_submitted_reminder_hours',
            str(self.not_submitted_reminder_hours or 4.0))
        self._apply_reminder_hour_to_cron()
        return {'type': 'ir.actions.act_window_close'}

    def _apply_reminder_hour_to_cron(self):
        """The "Daily Reminder Time" field is a friendly single place to
        set this instead of asking the admin to go find and edit the
        cron's own nextcall under Settings > Technical - but under the
        hood it's just updating that same real ir.cron record, not a
        separate scheduling mechanism."""
        cron = self.env.ref('otm_b2b_marketing.cron_otm_b2b_visit_reminders', raise_if_not_found=False)
        if not cron:
            return
        hour = int(self.reminder_hour or 9)
        minute = int(round((self.reminder_hour or 9) % 1 * 60))
        now = fields.Datetime.now()
        next_call = now.replace(hour=hour % 24, minute=minute, second=0, microsecond=0)
        if next_call <= now:
            next_call += timedelta(days=1)
        cron.sudo().write({'nextcall': next_call})

    def action_save_and_set_webhook(self):
        self.ensure_one()
        self.action_save()
        if requests is None:
            raise UserError(_('The "requests" Python package is not available on this server.'))
        if not self.bot_token:
            raise UserError(_('Enter the Bot Token first.'))

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if not base_url or 'localhost' in base_url:
            raise UserError(_(
                'web.base.url is not set to a public HTTPS address (Settings > Technical > '
                'System Parameters). Telegram needs a real public URL to deliver messages to.'))
        webhook_url = f"{base_url}/b2b/telegram/webhook"

        # Telegram's official webhook-authenticity mechanism: it echoes
        # this secret back in the X-Telegram-Bot-Api-Secret-Token header
        # on every request, so our controller can reject anything that
        # didn't actually come from Telegram.
        params_env = self.env['ir.config_parameter'].sudo()
        secret_token = params_env.get_param('otm_b2b_marketing.telegram_webhook_secret')
        if not secret_token:
            secret_token = uuid.uuid4().hex
            params_env.set_param('otm_b2b_marketing.telegram_webhook_secret', secret_token)

        try:
            response = requests.post(
                f'https://api.telegram.org/bot{self.bot_token}/setWebhook',
                json={'url': webhook_url, 'secret_token': secret_token},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise UserError(_('Could not reach Telegram: %s', exc))

        data = response.json() if response.ok else {}
        if response.ok and data.get('ok'):
            self.webhook_status = _('Webhook set successfully to %s', webhook_url)
        else:
            self.webhook_status = _('Failed: %s', response.text)
            raise UserError(_('Telegram rejected the webhook setup: %s', response.text))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'otm.b2b.telegram.settings.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
