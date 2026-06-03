"""
Arms controller. If a value is missing from any side, the corresponding hand
returns to its lowered home pose, after which the next command is dispatched.
"""

import signal
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import serial

from anushka_runtime.config import CONTROL_FILES, LEFT_ARM_MEGA_PORT, RIGHT_ARM_MEGA_PORT, STATUS_FILES
from anushka_runtime.ipc import append_message, open_reader, read_available
from Arms.gesture_registry import resolve_gesture

leftCommand = "ARM:90,90,90,90"
rightCommand = "ARM:90,90,90,90"

lefth = None
righth = None

_shutdown_requested = False


def _on_signal(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True


def _diag(message: str) -> None:
    append_message(STATUS_FILES["haath"], message)
    try:
        sys.stderr.write(f"[arms] {message}\n")
        sys.stderr.flush()
    except Exception:
        pass


def report_nonfatal(message):
    append_message(CONTROL_FILES["monitor"], f"Error- [NON FATAL] {message}")
    try:
        sys.stderr.write(f"[arms] {message}\n")
        sys.stderr.flush()
    except Exception:
        pass


def send_line(board, payload, disconnect_message):
    if board is None:
        return False
    try:
        board.write(f"{payload}\n".encode("utf-8"))
        return True
    except Exception:
        report_nonfatal(disconnect_message)
        return False


def _open_arm(port, side_label):
    if not port:
        _diag(f"{side_label} arm Mega port not configured. Running in simulation mode for that side.")
        return None
    try:
        return serial.Serial(port, baudrate=9600, timeout=1)
    except Exception as exc:
        _diag(f"Could not open {side_label} arm Mega ({port}): {exc!s}. Running in simulation mode for that side.")
        return None


lefth = _open_arm(LEFT_ARM_MEGA_PORT, "left")
righth = _open_arm(RIGHT_ARM_MEGA_PORT, "right")


def setValsAll(ardObj, a1, a2, a3, a4, slow=False):
    command = f"ARM:{a1},{a2},{a3},{a4}"

    if ardObj is None:
        return

    if send_line(
        ardObj,
        command,
        "Arm Mega connection was interrupted recently. Please reattach it.",
    ):
        time.sleep(0.25 if slow else 0.1)
        global leftCommand
        global rightCommand
        if ardObj == lefth:
            leftCommand = command
        else:
            rightCommand = command


def setAllFingers(haathside, f1, f2, f3, f4, f5):
    board = righth if haathside == 1 else lefth
    values = [f1, f2, f3, f4, f5] if haathside == 1 else [180 - f1, 180 - f2, 180 - f3, 180 - f4, 180 - f5]
    payload = "HAND:" + ",".join(str(value) for value in values)
    send_line(
        board,
        payload,
        "Finger control on the arm Mega was interrupted recently. Please reattach it.",
    )


def homePalm(hand):
    setAllFingers(hand, 90, 90, 90, 90, 90)


def closePalm(hand):
    setAllFingers(hand, 170, 40, 40, 40, 40)


def openPalm(hand):
    setAllFingers(hand, 50, 130, 130, 130, 130)


def pointPalm(hand):
    setAllFingers(hand, 140, 130, 40, 50, 50)


def oneCountPalm(hand):
    setAllFingers(hand, 170, 140, 40, 40, 40)


def twoCountPalm(hand):
    setAllFingers(hand, 170, 140, 140, 40, 40)


def threeCountPalm(hand):
    setAllFingers(hand, 170, 140, 140, 140, 40)


def fourCountPalm(hand):
    setAllFingers(hand, 170, 140, 140, 140, 140)


def preachPalm(hand):
    setAllFingers(hand, 160, 140, 30, 60, 60)


def shakeHandPalm(hand):
    setAllFingers(hand, 90, 135, 115, 115, 115)


def salutePalm(hand):
    setAllFingers(hand, 170, 130, 130, 130, 130)


def middleFingerPalm(hand):
    setAllFingers(hand, 100, 40, 130, 40, 40)


def thumbsUpPalm(hand):
    setAllFingers(hand, 30, 40, 40, 40, 40)


def okayPalm(hand):
    setAllFingers(hand, 170, 45, 130, 130, 130)


def hornsPalm(hand):
    setAllFingers(hand, 160, 130, 40, 40, 130)


def mamamiahPalm(hand):
    setAllFingers(hand, 170, 90, 55, 55, 55)


def cheesePalm(hand):
    setAllFingers(hand, 170, 135, 135, 40, 40)


def jaaduTonaPalm():
    send_line(
        righth,
        "SPECIAL:JAADUTONA",
        "Finger control on the right arm Mega was interrupted recently. Please reattach it.",
    )


def callMePalm():
    setAllFingers(1, 30, 40, 40, 40, 130)


def homePos(ard):
    setValsAll(ard, 90, 90, 90, 90)


def shakeHand():
    setValsAll(righth, 80, 0, 75, 110, slow=True)


def take():
    setValsAll(righth, 80, 0, 75, 0, slow=True)


def Hi():
    setValsAll(righth, 180, 90, 15, 180, slow=True)


def pointLeft():
    homePos(lefth)


def countIt():
    setValsAll(righth, 180, 90, 15, 180, slow=True)


def thinkOnChin():
    setValsAll(righth, 125, 25, 0, 90)


def pointRight():
    homePos(righth)


def YawnStretch():
    setValsAll(righth, 90, 40, 20, 90)
    closePalm(1)
    time.sleep(2)
    setValsAll(lefth, 90, 40, 20, 90)
    closePalm(0)

    time.sleep(5)

    setValsAll(righth, 90, 90, 90, 90, slow=True)
    openPalm(1)
    time.sleep(2)
    setValsAll(lefth, 90, 90, 90, 90, slow=True)
    openPalm(0)


def Seedha(ard):
    if ard == lefth:
        setValsAll(ard, 180, 90, 160, 0, slow=True)
    elif ard == righth:
        setValsAll(ard, 0, 90, 160, 0, slow=True)


def salute():
    setValsAll(righth, 180, 0, 40, 180, slow=True)


def DownLeft():
    setValsAll(lefth, 180, 0, 90, 90, slow=True)


def DownRight():
    setValsAll(righth, 0, 0, 90, 90, slow=True)


def holdBouquet():
    setValsAll(righth, 115, 0, 40, 90)
    setValsAll(lefth, 125, 0, 30, 20)


def selfPoint():
    setValsAll(lefth, 90, 40, 25, 140, slow=True)


def Saamne(ard):
    setValsAll(ard, 90, 0, 90, 90)


def jaaduTona():
    setValsAll(righth, 90, 0, 90, 30)


def callMe():
    setValsAll(righth, 100, 75, 0, 90)


def do_home_open():
    homePos(lefth)
    openPalm(0)
    time.sleep(2)
    homePos(righth)
    openPalm(1)


def do_yawn_stretch():
    YawnStretch()


def do_shake_hand():
    shakeHand()
    shakeHandPalm(1)


def do_point_left():
    pointLeft()
    pointPalm(0)


def do_point_right():
    pointRight()
    pointPalm(1)


def do_open_right():
    Seedha(righth)
    openPalm(1)


def do_open_both():
    Seedha(lefth)
    Seedha(righth)


def do_preach():
    Seedha(righth)
    preachPalm(1)


def do_bouquet():
    holdBouquet()
    shakeHandPalm(0)
    shakeHandPalm(1)


def do_self_point():
    selfPoint()
    thumbsUpPalm(0)
    time.sleep(3)
    setValsAll(lefth, 90, 40, 75, 180)


def do_salute():
    salute()
    salutePalm(1)


def do_jaadu_tona():
    jaaduTona()
    jaaduTonaPalm()


def do_middle_finger():
    Seedha(righth)
    middleFingerPalm(1)


def do_thumbs_up():
    Saamne(righth)
    thumbsUpPalm(1)


def do_okay():
    Seedha(righth)
    okayPalm(1)


def do_horns():
    Seedha(righth)
    hornsPalm(1)


def do_mamamiah():
    Seedha(righth)
    mamamiahPalm(1)


def do_open_both_palms():
    Seedha(lefth)
    openPalm(0)
    time.sleep(1)
    Seedha(righth)
    openPalm(1)


def do_close_both_palms():
    Seedha(lefth)
    closePalm(0)
    time.sleep(1)
    Seedha(righth)
    closePalm(1)


def do_cheese():
    Seedha(righth)
    cheesePalm(1)


def do_take():
    take()
    shakeHandPalm(1)


def do_count_one():
    countIt()
    oneCountPalm(1)


def do_count_two():
    countIt()
    twoCountPalm(1)


def do_count_three():
    countIt()
    threeCountPalm(1)


def do_count_four():
    countIt()
    fourCountPalm(1)


def do_count_five():
    countIt()
    openPalm(1)


def do_magic_palm():
    Seedha(righth)
    jaaduTonaPalm()


def do_call_me():
    callMe()
    callMePalm()


def do_close_together():
    Seedha(lefth)
    closePalm(0)
    Seedha(righth)
    time.sleep(2)
    closePalm(1)


GESTURE_ACTIONS = {
    "1": do_home_open,
    "2": do_yawn_stretch,
    "3": do_shake_hand,
    "4": do_point_left,
    "5": do_point_right,
    "6": do_open_right,
    "7": do_open_both,
    "8": do_preach,
    "9": do_bouquet,
    "10": lambda: None,
    "11": do_self_point,
    "12": do_salute,
    "13": do_jaadu_tona,
    "14": do_middle_finger,
    "15": do_thumbs_up,
    "16": do_okay,
    "17": do_horns,
    "18": do_mamamiah,
    "19": lambda: None,
    "20": do_open_both_palms,
    "21": do_close_both_palms,
    "22": do_cheese,
    "23": do_take,
    "24": do_count_one,
    "25": do_count_two,
    "26": do_count_three,
    "27": do_count_four,
    "28": do_count_five,
    "29": do_magic_palm,
    "30": do_call_me,
    "31": do_close_together,
}


def _safe_close():
    for board, label in ((lefth, "left"), (righth, "right")):
        if board is not None:
            try:
                board.close()
            except Exception as exc:
                _diag(f"Failed to close {label} arm Mega: {exc!s}")


def execute_gesture(command: str) -> bool:
    spec = resolve_gesture(command)
    command_code = spec.code if spec is not None else command
    action = GESTURE_ACTIONS.get(command_code)
    if action is None:
        _diag(f"Unknown arm gesture command: {command!r}")
        return False

    action()
    return True


def main() -> None:
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    haathWS = open_reader(CONTROL_FILES["haath"])

    HANDS_UPLIFT_TIME = 6

    # Bring the hands to a known starting pose. In simulation mode these are no-ops.
    DownLeft()
    homePalm(0)
    DownRight()
    time.sleep(1)
    homePalm(1)

    append_message(STATUS_FILES["haath"], "1")

    chaalu = False
    special = False
    prevTime = time.time()

    try:
        while True:
            if _shutdown_requested:
                break

            newRead = read_available(haathWS)
            newTime = time.time()

            if chaalu:
                time.sleep(1)
                if newTime - prevTime >= HANDS_UPLIFT_TIME:
                    if special:
                        DownLeft()
                        closePalm(0)
                        time.sleep(0.4)
                        DownRight()
                        closePalm(1)
                        time.sleep(3)
                        homePalm(0)
                        time.sleep(1)
                        homePalm(1)
                        chaalu = False
                        time.sleep(3)
                        special = False
                    else:
                        DownLeft()
                        homePalm(0)
                        DownRight()
                        time.sleep(1)
                        homePalm(1)
                        chaalu = False
                        time.sleep(3)
                continue

            if not newRead:
                time.sleep(0.05)
                continue

            prevTime = newTime
            chaalu = True

            if newRead == "-1":
                DownLeft()
                DownRight()
                break

            special = newRead == "6"

            execute_gesture(newRead)

            time.sleep(0.2)
    finally:
        try:
            haathWS.close()
        except Exception:
            pass
        append_message(STATUS_FILES["haath"], "2")
        _safe_close()


if __name__ == "__main__":
    main()
