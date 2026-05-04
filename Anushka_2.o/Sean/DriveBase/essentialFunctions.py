import serial
import sys
import time
import nums_from_string
import math
import words2num
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from runtime_helpers import *
from Speech.essentialFunctions import *

###############COMMANDS################
leftMotorSet= b"\x4e\x45\x58\x96\x10\x00\x17" #Left motor velocity
rightMotorSet= b"\x4e\x45\x58\x95\x10\x00\x18" #Right motor velocity
forcommand= b"\x4e\x45\x58\x94\x01\x80"
backcommand= b"\x4e\x45\x58\x94\x02\x7f"
leftcommand= b"\x4e\x45\x58\x94\x03\x7e"
rightcommand= b"\x4e\x45\x58\x94\x04\x7d"
turnOnIRcommand= b"\x4e\x45\x58\x09\x09\x03"
getIRDatacommand= b"\x4e\x45\x58\x05\x03\x0d"
###############COMMANDS################

###############INITIALSING################
def initPortForFirebird():
    obj= serial.Serial('COM7', baudrate= 57600, timeout= 1, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS)
    obj.write(leftMotorSet)
    time.sleep(1)

    obj.write(rightMotorSet)
    time.sleep(1)

def initPortForNeck():
    neckObj= serial.Serial('COM8', baudrate= 57600, timeout= 2)
    neckObj.write(turnOnIRcommand)

###############INITIALISING################

def move(direction, steps):
    for _ in range(math.floor(steps)):
        obj.write(direction)
        time.sleep(1)

def getIRVal():
    try:
        obj.write(getIRDatacommand)
        datas= obj.readline()
        print(datas)
        datas= datas[5:-1].decode()
        print(datas) #String value
        lst= eachVal(datas)
        return lst
    except:
        speak("Maintain your limits please. You are too close")
        time.sleep(2)

def eachVal(st):
    ls= []
    for i in range(len(st)):
        ls.append(ord(st[i]))
    return ls
        # time.sleep(1)

def extractStep(st):
    try:
        k= int(nums_from_string.get_nums(st)[0])
        return k
    except:
        pass

    for word in st.split(" "):
        try:
            j= int(words2num.w2n(word))
            return j
        except:
            return 1
        #Left / right  this fxn is not called.

def stopFirebird():
    stopcommand= b"\x4e\x45\x58\x94\x06\x7b"
    obj.write(stopcommand)

def followMe():
    #Banao poora
    pass

def RollsRoyce(query):
    if "left" in comm:
        move(leftcommand, 2.3)
    elif "right" in comm:
        move(rightcommand, 2.3)
    elif "forward" in comm or "ahead" in comm:
        step= extractStep(comm)
        print(step)
        move(forcommand, step)
    elif ListCheck(["back", "behind", "reverse"], comm):
        step= extractStep(comm)
        move(backcommand, step)
    
    stopFirebird()
if __name__ == "__main__":
    while True:
        initPortForFirebird()
        comm= input("Enter command: ")
        RollsRoyce(comm)
    

    
