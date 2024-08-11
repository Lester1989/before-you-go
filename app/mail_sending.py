import resend
import os
has_api_key = os.environ.get('RESEND_API_KEY') is not None
if has_api_key:
    resend.api_key = os.environ.get('RESEND_API_KEY')

def send_test_email(to_mail:str):
    if not has_api_key:
        return False
    return resend.Emails.send({
        "from": os.environ.get('RESEND_DOMAIN'),
        "to": to_mail,
        "subject": "Hello World",
        "html": "<p>Congrats on sending your <strong>first email</strong> from Before you go!</p>",
        "text": "Congrats on sending your first email from Before you go!",
    })

def send_registration_mail(to_mail:str,token:str):
    if not has_api_key:
        return False
    print(f'start sending registration mail to {to_mail}')
    send_result = resend.Emails.send({
        "from": os.environ.get('RESEND_DOMAIN'),
        "to": to_mail,
        "subject": "Confirm your registration",
        "html": f"<p>Thanks for registering! Please confirm your registration by clicking <a href='{os.environ.get('BASE_URL')}/confirm_registration/{token}'>here</a></p>",
        "text": f"Thanks for registering! Please confirm your registration by clicking {os.environ.get('BASE_URL')}/confirm_registration/{token}"
    })
    print(send_result)
    return send_result

def send_password_reset_mail(to_mail:str,user_id:str,reset_id:str):
    if not has_api_key:
        return False
    print(f'start sending reset mail to {to_mail}')
    send_result = resend.Emails.send({
        "from": os.environ.get('RESEND_DOMAIN'),
        "to": to_mail,
        "subject": "Reset your password",
        "html": f"<p> Sorry you forgot your password. Please reset your password by clicking <a href='{os.environ.get('BASE_URL')}/password_reset/{reset_id}/{user_id}'>here</a></p>",
        "text": f"Sorry you forgot your password. Please reset your password by clicking {os.environ.get('BASE_URL')}/password_reset/{reset_id}/{user_id}"
    })
    print(send_result)
    return send_result
