import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RETURN_IMAGE_PATH = REPO_ROOT / "Sean" / "Resources" / "return.jpg"

# Email and password of the sender
email = 'himeshvijay89@gmail.com'
password = 'Hivi@862004'

# Email details
subject = 'Qaid Mein Bulbul'
recipient = 'himeshvijay89@gmail.com'
body = 'Heya pai. Ki haal chaal? Sab changa? Mai aa rahi hu. Super soon! 😊😁❣'

# Create a Multipart message to include a text message and an image attachment
msg = MIMEMultipart()
msg['Subject'] = subject
msg['From'] = email
msg['To'] = recipient

# Add the body of the email
msg.attach(MIMEText(body, 'plain'))

# Add an image attachment
with RETURN_IMAGE_PATH.open('rb') as f:
    img_data = f.read()
    image = MIMEImage(img_data, name='image.jpg')
    msg.attach(image)

# Create a SMTP session
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()

# Login to the sender email account
server.login(email, password)

# Send the email
server.sendmail(email, recipient, msg.as_string())

# Terminate the SMTP session
server.quit()
