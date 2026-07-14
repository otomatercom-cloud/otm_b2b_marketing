# -*- coding: utf-8 -*-
import json
import logging
import uuid

from odoo import http
from odoo.http import request

from ..models.otm_b2b_telegram import _otm_telegram_api_send

_logger = logging.getLogger(__name__)


class OtmB2bTelegramController(http.Controller):
    """Receives Telegram Bot API webhook updates. Its only real job is
    the /start <token> handshake that automatically maps a Telegram chat
    to the Odoo user who generated that token - see models/
    otm_b2b_telegram.py for the full explanation of the flow."""

    @http.route('/b2b/telegram/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def telegram_webhook(self, **kwargs):
        params = request.env['ir.config_parameter'].sudo()
        expected_secret = params.get_param('otm_b2b_marketing.telegram_webhook_secret')
        received_secret = request.httprequest.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if expected_secret and received_secret != expected_secret:
            # Doesn't match what Telegram itself would send back per the
            # secret_token set during setWebhook - reject silently.
            _logger.warning('otm_b2b_marketing: Telegram webhook called with invalid/missing secret token.')
            return request.make_json_response({'ok': False}, status=403)

        try:
            update = json.loads(request.httprequest.data or b'{}')
        except ValueError:
            return request.make_json_response({'ok': False}, status=400)

        message = update.get('message') or update.get('edited_message') or {}
        chat = message.get('chat') or {}
        chat_id = chat.get('id')
        text = (message.get('text') or '').strip()

        if chat_id and text.startswith('/start'):
            self._handle_start(chat_id, text)
        # Any other message type/content is intentionally ignored - this
        # bot only exists to deliver reminders/links, not to hold a
        # two-way conversation.

        return request.make_json_response({'ok': True})

    def _handle_start(self, chat_id, text):
        parts = text.split(maxsplit=1)
        token = parts[1].strip() if len(parts) > 1 else ''
        env = request.env

        if not token:
            _otm_telegram_api_send(
                env, chat_id,
                "Hi! Open the B2B Marketing dashboard in Odoo and tap 'Connect Telegram' "
                "to link this chat to your account."
            )
            return

        user = env['res.users'].sudo().search([('otm_telegram_link_token', '=', token)], limit=1)
        if not user:
            _otm_telegram_api_send(
                env, chat_id,
                "This connect link isn't valid anymore. Go back to the B2B Marketing dashboard "
                "and tap 'Connect Telegram' again for a fresh link."
            )
            return

        # Regenerate the token immediately after a successful link so the
        # same link/token can't be reused by someone else to hijack a
        # different chat onto this user's account.
        user.sudo().write({
            'otm_telegram_chat_id': str(chat_id),
            'otm_telegram_link_token': uuid.uuid4().hex,
        })
        _otm_telegram_api_send(
            env, chat_id,
            f"You're connected, {user.name}! You'll get visit reminders and portal links here."
        )
