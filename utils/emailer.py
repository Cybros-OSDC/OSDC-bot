import aiosmtplib
from email.message import EmailMessage
from config import Config

async def send_email(recipient_email, otp_code):
    """Send OTP email to recipient"""
    msg = EmailMessage()
    msg['From'] = Config.EMAIL_USERNAME
    msg['To'] = recipient_email
    msg['Subject'] = 'LNMIIT Discord Verification'
    msg.set_content(f'Your OTP for Discord verification is: {otp_code}')
    
    try:
        await aiosmtplib.send(
            msg,
            hostname='smtp.gmail.com',
            port=587,
            start_tls=True,
            username=Config.EMAIL_USERNAME,
            password=Config.EMAIL_PASSWORD
        )
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False
