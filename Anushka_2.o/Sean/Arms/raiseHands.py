  
import serial
import time
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from Speech.essentialFunctions import *

HAATH_EF_FILE = SEAN_ROOT / "Arms" / "armsEF.txt"
MONITOR_WS_FILE = SEAN_ROOT / "Monitor" / "monitorWS.txt"

leftCommand= f"#1ZA#2ZA#3ZA#4ZA#5ZA#6ZA****"
rightCommand= f"#1ZA#2ZA#3ZA#4ZA#5ZA#6ZA****"

####################### PORT  SETTING #########################
leftPortNum= 3
rightPortNum= 4
PalmPort = 20

def portStr(i):
    return ("COM"+str(i))

try:
    lefth= serial.Serial(portStr(leftPortNum), baudrate= 9600, timeout=1)
    speak(f"Left hand port set on {leftPortNum} successfully")
except:
    ef= open(HAATH_EF_FILE, 'a')
    ef.write("Problem in allocating port for left hand")
    ef.close()
    exit()

try:
    righth= serial.Serial(portStr(rightPortNum), baudrate= 9600, timeout=1)
    speak(f"Right hand port set on {rightPortNum} successfully")
except:
    ef= open(HAATH_EF_FILE, 'a')
    ef.write("Problem in allocating port for right hand")
    ef.close()
    exit()

try:
    Palm= serial.Serial(portStr(PalmPort), baudrate= 9600, timeout=3)
    speak(f"Palms port set on {PalmPort} successfully")
except:
    ef= open(HAATH_EF_FILE, 'a')
    ef.write("Problem in allocating port for Palm Arduino.")
    ef.close()
    exit()
####################### /PORT  SETTING #########################


####################### ARMS MANIPULATION #########################
def setValsAll(ardObj, a1,a2,a3,a4, slow= False):
    
    if slow:
        command= f"#1{chr(a1)}{chr(30)}#2{chr(a2)}{chr(30)}#3{chr(a3)}{chr(30)}#4Z{chr(30)}#5{chr(a4)}A#6Z{chr(30)}****"    
    else:
        command= f"#1{chr(a1)}{chr(50)}#2{chr(a2)}A#3{chr(a3)}A#4ZA#5{chr(a4)}A#6ZA****"
    
    try:
        ardObj.write(command.encode())
        time.sleep(0.7)
        global leftCommand
        global rightCommand
        if ardObj == lefth:
            leftCommand= command
        else:
            rightCommand= command
    except:
        if ardObj == lefth:
            monitorWS= open(MONITOR_WS_FILE, 'a')
            monitorWS.write("Error- [NON FATAL] Left Hand port has been fiddled with recently, due to which the connection broke. Please reattach it")
            monitorWS.close()
        else:
            monitorWS= open(MONITOR_WS_FILE, 'a')
            monitorWS.write("Error- [NON FATAL] Right Hand port has been fiddled with recently, due to which the connection broke. Please reattach it")
            monitorWS.close()
        pass

def setAllFingers(haathside, f1,f2,f3,f4,f5):
    
    if haathside == 1:
        lis= [str(haathside), str(f1), str(f2), str(f3), str(f4), str(f5)]
    else:
        lis= [str(haathside), str(180-f1), str(180-f2), str(180-f3), str(180-f4), str(180-f5)]
    st= "#".join(lis)
    try:
        Palm.write(st.encode()) #Palmport ek hi hai for both hands, don't worry
    except:
        monitorWS= open(MONITOR_WS_FILE, 'a')
        monitorWS.write("Error- [NON FATAL] Palms port has been fiddled with recently, due to which the connection broke. Please reattach it")
        monitorWS.close()


def homePos(ard):
    setValsAll(ard, 90,90,90,90)

homePos(lefth)
homePos(righth)
