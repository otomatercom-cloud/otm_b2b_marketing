# -*- coding: utf-8 -*-
import logging
import uuid

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover - requests ships with Odoo by default
    requests = None


class ResUsers(models.Model):
    """Adds a self-service Telegram connection to each user, so B2B
    Marketing officers can receive visit reminders and portal links on
    Telegram without anyone ever typing in a chat ID by hand.

    How the automatic mapping works (Telegram "deep link" handshake):
    1. Each user has a unique otm_telegram_link_token (regenerated after
       every successful connect, so an old link can't be reused).
    2. otm_telegram_deep_link builds https://t.me/<bot>?start=<token>.
    3. The officer taps that link on their phone -> Telegram opens a chat
       with the bot and auto-sends "/start <token>".
    4. Our public webhook (controllers/telegram_webhook.py) receives that
       update, looks up the user by token, and stores the chat_id it came
       from. No manual entry anywhere in this flow.
    """
    _inherit = 'res.users'

    otm_telegram_chat_id = fields.Char(string='Telegram Chat ID', copy=False, readonly=True)
    otm_telegram_link_token = fields.Char(
        string='Telegram Link Token', copy=False, readonly=True,
        default=lambda self: uuid.uuid4().hex)
    otm_telegram_connected = fields.Boolean(
        string='Telegram Connected', compute='_compute_otm_telegram_connected')
    otm_telegram_deep_link = fields.Char(
        string='Telegram Connect Link', compute='_compute_otm_telegram_deep_link')

    @api.depends('otm_telegram_chat_id')
    def _compute_otm_telegram_connected(self):
        for user in self:
            user.otm_telegram_connected = bool(user.otm_telegram_chat_id)

    @api.depends('otm_telegram_link_token')
    def _compute_otm_telegram_deep_link(self):
        bot_username = self.env['ir.config_parameter'].sudo().get_param('otm_b2b_marketing.telegram_bot_username')
        for user in self:
            user.otm_telegram_deep_link = (
                f"https://t.me/{bot_username}?start={user.otm_telegram_link_token}"
                if bot_username and user.otm_telegram_link_token else False
            )

    def action_regenerate_telegram_link(self):
        """Invalidate the current link (and any chat already linked
        through it) and issue a fresh one - e.g. the officer switched
        phones, or blocked/deleted the old chat with the bot."""
        for user in self:
            user.write({
                'otm_telegram_link_token': uuid.uuid4().hex,
                'otm_telegram_chat_id': False,
            })

    def action_disconnect_telegram(self):
        """Clear the stored chat_id only, keep the same link token so the
        officer can reconnect later without needing a brand new link.
        _otm_telegram_send() checks otm_telegram_chat_id before every
        single send, so the moment this is cleared, ALL notifications to
        this person stop immediately - reminders, check-in/out
        confirmations, MOU alerts, everything - with no separate
        per-notification-type flag to also remember to turn off."""
        for user in self:
            user.write({'otm_telegram_chat_id': False})

    @api.model
    def action_disconnect_telegram_self(self):
        """Convenience wrapper so callers (like the dashboard widget)
        that only know "the current user", not an explicit id, can still
        trigger a disconnect via a plain @api.model RPC call."""
        self.env.user.action_disconnect_telegram()

    def action_send_telegram_test(self):
        self.ensure_one()
        if not self.otm_telegram_chat_id:
            return
        self._otm_telegram_send(
            'This is a test message from B2B Marketing - Logic School Of Management. '
            'Your Telegram is connected correctly.'
        )

    def _otm_telegram_send(self, text):
        """Send a plain-text Telegram message to this user, if connected.
        Fails silently (logged, not raised) so a Telegram outage never
        blocks the actual business flow (check-in, reminders, etc.)."""
        self.ensure_one()
        if not self.otm_telegram_chat_id:
            return False
        return _otm_telegram_api_send(self.env, self.otm_telegram_chat_id, text)

    @api.model
    def _otm_telegram_notify_heads(self, text):
        """Send a Telegram message to every user holding the Marketing
        Head group, automatically - no per-record configuration needed.
        Membership is read live from the group each time, so promoting or
        removing someone from Marketing Head immediately changes who gets
        these without touching this module at all."""
        head_group = self.env.ref('otm_b2b_marketing.group_otm_b2b_marketing_head', raise_if_not_found=False)
        if not head_group:
            return
        for head in head_group.user_ids:
            if head.otm_telegram_connected:
                head._otm_telegram_send(text)


def _otm_telegram_api_send(env, chat_id, text):
    """Low-level call to Telegram's sendMessage API. Standalone function
    (not tied to a recordset) so the webhook controller can also use it
    to reply during the /start handshake before any res.users context is
    relevant."""
    if requests is None:
        _logger.warning('otm_b2b_marketing: python "requests" package not available, cannot send Telegram message.')
        return False
    bot_token = env['ir.config_parameter'].sudo().get_param('otm_b2b_marketing.telegram_bot_token')
    if not bot_token:
        _logger.info('otm_b2b_marketing: Telegram bot token not configured, skipping send.')
        return False
    try:
        response = requests.post(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            json={'chat_id': chat_id, 'text': text},
            timeout=10,
        )
        if not response.ok:
            _logger.warning('otm_b2b_marketing: Telegram sendMessage failed: %s', response.text)
        return response.ok
    except requests.RequestException as exc:
        _logger.warning('otm_b2b_marketing: Telegram sendMessage error: %s', exc)
        return False


class OtmB2bTelegramTemplate(models.Model):
    """Editable message text for each notification event, so the wording
    can be changed from Configuration without touching code. Placeholders
    are plain Python str.format() fields - each event documents which
    ones it fills in (see the 'placeholders' help text and the seed data
    in data/otm_b2b_telegram_template_data.xml)."""
    _name = 'otm.b2b.telegram.template'
    _description = 'B2B Telegram Message Template'
    _order = 'code'

    code = fields.Selection([
        ('visit_planned', 'Visit Planned (sent to the officer on Confirm)'),
        ('visit_reminder_today', "Today's Visit Reminder"),
        ('visit_not_submitted', "Visit Not Submitted Reminder"),
        ('visit_completed', 'Visit Completed Confirmation'),
        ('mou_expiry', 'MOU Expiry Reminder'),
        ('mou_signed', 'MOU Signed Notification (to Marketing Head)'),
    ], string='Event', required=True)
    name = fields.Char(string='Name', required=True)
    body = fields.Text(string='Message Template', required=True)
    placeholders_help = fields.Char(string='Available Placeholders', readonly=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Only one template is allowed per event.'),
    ]

    @api.model
    def _render(self, code, **context):
        """Look up the active template for this event and fill in the
        placeholders. Falls back to the raw (unfilled) template text if a
        placeholder is missing, rather than raising and blocking whatever
        business flow triggered the send - a typo in an admin-edited
        template should never break check-in/check-out/reminders."""
        template = self.sudo().search([('code', '=', code), ('active', '=', True)], limit=1)
        if not template:
            return None
        try:
            return template.body.format(**context)
        except (KeyError, IndexError, ValueError):
            _logger.warning(
                'otm_b2b_marketing: Telegram template "%s" has a placeholder that doesn\'t '
                'match what was provided (%s) - sending the raw template text instead.',
                code, list(context.keys())
            )
            return template.body
