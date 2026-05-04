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

leftCommand= f"#1ZA#2ZA#3ZA#4ZA#5ZA#6ZA****"
rightCommand= f"#1ZA#2ZA#3ZA#4ZA#5ZA#6ZA****"

def portStr(i):
    return ("COM"+str(i))
    
def setValsAll(ardObj, a1,a2,a3,a4,a5,a6):
    command= f"#1{chr(a1)}{chr(50)}#2{chr(a2)}A#3{chr(a3)}A#4{chr(a4)}A#5{chr(a5)}A#6{chr(a6)}A****"
    ardObj.write(command.encode())
    time.sleep(0.1)
    if ardObj == lefth:
        leftCommand= command
    else:
        rightCommand= command

def setVals(ardObj, motor, val):
    if ardObj == lefth:
        command= leftCommand
    else:
        command= rightCommand
    
    motor= str(motor)
    newStr= f"{motor}{chr(val)}{chr(60)}"
    place= command.index(motor)
    oldStr= command[place:place+3]
    command= command.replace( oldStr, newStr)
    ardObj.write(command.encode())

def homePos(ard):
    give= f"#1ZZ#2ZZ#3ZZ#4ZZ#5ZZ#6ZZ****"
    ard.write(give.encode())

def shakeHand():
    setValsAll(lefth, 70, 110, 140, 90, 90, 90)

def poora():
    setValsAll(lefth, 70, 110, 140, 60, 60, 60)

def tst():
    poora()
    time.sleep(0.5)
    homePos(lefth)
    time.sleep(0.5)

if __name__ == "__main__":
    # lefth, righth= setPorts() 
    lefth= serial.Serial(portStr(6), baudrate= 9600, timeout=1)
    for x in range(10):
        tst()
        print(x)
