from twilio.rest import Client

account_sid = 'ACbf158b40c375f1d9fd19a21db915aef'
auth_token = 'f612dd5cfdd15c4e5106db42092b74c'

from_number = '+9454279072'
to_number = '+919115354573'

message= input("Enter message or leave blank to send default msg")
if not message:
    message = "Hello mom. This is Himesh sir's automation message speaking. Sir wants to drink tea. Can you please make tea for him? Thankyou, and have a nice day."

print(message)

client = Client(account_sid, auth_token)

call = client.calls.create(
    from_=from_number,
    to=to_number,
    twiml='<Response><Say>' + message + '</Say></Response>'
)

print(call.sid)
