"""HTTPS mail transport. No durable token/message outbox and no message-body logs."""
from email.utils import parseaddr

import httpx
from .config import settings

# Only test code can read this process-local mailbox. Never exposed by an API.
test_mailbox = []

def _sender():
    name, address = parseaddr(settings.email_from)
    if not address or '@' not in address or any(character in settings.email_from for character in '\r\n'):
        return None
    return {'name': name or 'Agent Meadow', 'email': address}

def available():
    return settings.email_provider == 'test' and settings.environment == 'test' or (
        settings.email_provider in ('brevo', 'resend') and bool(settings.email_api_key and _sender()))

def send(recipient, purpose, link):
    subjects = {'reset':'Reset your Agent Meadow password','verify':'Verify your Agent Meadow email','setup':'Set up your Agent Meadow password'}
    text = subjects[purpose] + '\n\nOpen this private link:\n' + link + '\n\nIf you did not request this, ignore this message. Never share this link.'
    if settings.email_provider == 'test' and settings.environment == 'test':
        test_mailbox.append({'recipient':recipient,'purpose':purpose,'link':link})
        return True
    if not available(): return False
    try:
        with httpx.Client(timeout=10,follow_redirects=False) as client:
            if settings.email_provider == 'brevo':
                response=client.post('https://api.brevo.com/v3/smtp/email',
                    headers={'api-key':settings.email_api_key,'accept':'application/json'},
                    json={'sender':_sender(),'to':[{'email':recipient}],
                          'subject':subjects[purpose],'textContent':text})
            elif settings.email_provider == 'resend':
                response=client.post('https://api.resend.com/emails',
                    headers={'Authorization':'Bearer '+settings.email_api_key},
                    json={'from':settings.email_from,'to':[recipient],
                          'subject':subjects[purpose],'text':text})
            else:
                return False
        return 200 <= response.status_code < 300
    except httpx.HTTPError:
        # Do not log exceptions/response bodies: upstream messages may echo links.
        return False
