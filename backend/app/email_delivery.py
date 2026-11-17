"""HTTPS mail transport. No durable token/message outbox and no message-body logs."""
import httpx
from .config import settings

# Only test code can read this process-local mailbox. Never exposed by an API.
test_mailbox = []

def available():
    return settings.email_provider == 'test' and settings.environment == 'test' or (
        settings.email_provider == 'resend' and bool(settings.email_api_key and settings.email_from))

def send(recipient, purpose, link):
    subjects = {'reset':'Reset your Agent Meadow password','verify':'Verify your Agent Meadow email','setup':'Set up your Agent Meadow password'}
    text = subjects[purpose] + '\n\nOpen this private link:\n' + link + '\n\nIf you did not request this, ignore this message. Never share this link.'
    if settings.email_provider == 'test' and settings.environment == 'test':
        test_mailbox.append({'recipient':recipient,'purpose':purpose,'link':link})
        return True
    if settings.email_provider != 'resend' or not available(): return False
    try:
        with httpx.Client(timeout=10,follow_redirects=False) as client:
            response=client.post('https://api.resend.com/emails',
                headers={'Authorization':'Bearer '+settings.email_api_key},
                json={'from':settings.email_from,'to':[recipient],'subject':subjects[purpose],'text':text})
        return 200 <= response.status_code < 300
    except httpx.HTTPError:
        # Do not log exceptions/response bodies: upstream messages may echo links.
        return False
