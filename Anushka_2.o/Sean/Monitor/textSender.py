import requests
import json

# Set the URL of the remote server's endpoint
url = "http://10.21.69.5:3000/"
endPoint= ""

# Set the string text you want to send
text = input("Enter text")

# Create a dictionary with the payload data
if text.startswith("Error-"):
    endPoint= "error/"
    url= url+endPoint
    text= text.replace("Error- ", "")
    payload = {"text": text}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(payload), headers=headers)

elif text.startswith("Log-"):
    endPoint= "log/"
    url= url+endPoint
    text= text.replace("Log- ", "")
    payload = {"text": text}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(payload), headers=headers)

elif text.startswith("StartTime- "):
    endPoint= "start-time/"
    url= url+endPoint
    text= text.replace("StartTime- ", "")
    payload = {"text": text}
    headers = {"Content-Type": "application/json"}
    response = requests.put(url, data=json.dumps(payload), headers=headers)

elif text.startswith("StopTime- "):
    endPoint= "stop-time/"
    url= url+endPoint
    text= text.replace("StopTime- ", "")
    payload = {"text": text}
    headers = {"Content-Type": "application/json"}
    response = requests.put(url, data=json.dumps(payload), headers=headers)

elif text.startswith("Battery-"):
    endPoint= "battery/"
    url= url+endPoint
    text= text.replace("Battery- ", "")
    payload = {"text": text}
    headers = {"Content-Type": "application/json"}
    response = requests.put(url, data=json.dumps(payload), headers=headers)

elif text.startswith("PrintJob-"):
    endPoint= "print-job/"
    url= url+endPoint
    text= text.replace("PrintJob- ", "")
    payload = {"text": text}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(payload), headers=headers)

# Check the response status code
print("Request replied with code:", response.status_code)
