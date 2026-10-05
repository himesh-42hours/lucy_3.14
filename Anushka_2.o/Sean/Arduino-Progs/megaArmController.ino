#include <Servo.h>

/*
  Single-arm Mega (11 servos):
  0 shoulder rotate
  1 shoulder lift A
  2 shoulder lift B
  3 elbow lift A
  4 elbow lift B
  5 wrist rotate
  6 thumb
  7 index
  8 middle
  9 ring
  10 pinky

  Serial commands:
    HOME
    ARM:sr,sl,el,wr
    HAND:f1,f2,f3,f4,f5
    RAW:a0,a1,a2,a3,a4,a5,a6,a7,a8,a9,a10
    GESTURE:WAVE / POINT / OPEN / FIST

  Set ARM_IS_LEFT and update pin/reverse arrays for each Mega.
*/

  ARM:a1,a2,a3,a4
  HAND:f1,f2,f3,f4,f5

#if ARM_IS_LEFT
const uint8_t ARM_PINS[11] = {2, 3, 4, 5, 6, 7, 22, 23, 24, 25, 26};
const bool ARM_REVERSE[11] = {false, true, false, true, false, false, false, false, false, false, false};
#else
const uint8_t ARM_PINS[11] = {8, 9, 10, 11, 12, 13, 27, 28, 29, 30, 31};
const bool ARM_REVERSE[11] = {false, true, false, true, false, false, false, false, false, false, false};
#endif

const int HOME_POS[11] = {0, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90};

const int FINGER_OPEN = 30;
const int FINGER_CLOSED = 150;

Servo servos[11];
int currentPos[11] = {0, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90};
bool servoAttached[11] = {false, false, false, false, false, false, false, false, false, false, false};

String incoming;

enum ServoIndex {
  SHOULDER_ROT = 0,
  SHOULDER_LIFT_A = 1,
  SHOULDER_LIFT_B = 2,
  ELBOW_LIFT_A = 3,
  ELBOW_LIFT_B = 4,
  WRIST_ROT = 5,
  THUMB = 6,
  INDEX_F = 7,
  MIDDLE_F = 8,
  RING_F = 9,
  PINKY_F = 10
};

int clampAngle(int value) {
  if (value < 0) return 0;
  if (value > 180) return 180;
  return value;
}

int nextValue(String &payload, int &cursor) {
  int comma = payload.indexOf(',', cursor);
  String token;
  if (comma == -1) {
    token = payload.substring(cursor);
    cursor = payload.length();
  } else {
    token = payload.substring(cursor, comma);
    cursor = comma + 1;
  }
  token.trim();
  return clampAngle(token.toInt());
}

void writeServo(int index, int angle) {
  angle = clampAngle(angle);
  currentPos[index] = angle;
  if (!servoAttached[index]) {
    servos[index].attach(ARM_PINS[index]);
    servoAttached[index] = true;
  }
  servos[index].write(ARM_REVERSE[index] ? 180 - angle : angle);
}

void moveSmooth(const int *targets, int count, int delayMs) {
  bool changed = true;
  while (changed) {
    changed = false;
    for (int i = 0; i < count; i++) {
      if (currentPos[i] < targets[i]) {
        writeServo(i, currentPos[i] + 1);
        changed = true;
      } else if (currentPos[i] > targets[i]) {
        writeServo(i, currentPos[i] - 1);
        changed = true;
      }
    }
    delay(delayMs);
  }
}

void setArmPose(int shoulderRot, int shoulderLift, int elbowLift, int wristRot) {
  int targets[11];
  for (int i = 0; i < 11; i++) targets[i] = currentPos[i];
  targets[SHOULDER_ROT] = shoulderRot;
  targets[SHOULDER_LIFT_A] = shoulderLift;
  targets[SHOULDER_LIFT_B] = shoulderLift;
  targets[ELBOW_LIFT_A] = elbowLift;
  targets[ELBOW_LIFT_B] = elbowLift;
  targets[WRIST_ROT] = wristRot;
  moveSmooth(targets, 11, 10);
}

void setHandPose(int f1, int f2, int f3, int f4, int f5) {
  int targets[11];
  for (int i = 0; i < 11; i++) targets[i] = currentPos[i];
  targets[THUMB] = f1;
  targets[INDEX_F] = f2;
  targets[MIDDLE_F] = f3;
  targets[RING_F] = f4;
  targets[PINKY_F] = f5;
  moveSmooth(targets, 11, 10);
}

void setRawPose(String payload) {
  int targets[11];
  int cursor = 0;
  for (int i = 0; i < 11; i++) {
    targets[i] = nextValue(payload, cursor);
  }
  moveSmooth(targets, 11, 8);
}

void goHome() {
  moveSmooth(HOME_POS, 11, 10);
}

void gestureOpenHand() {
  setHandPose(FINGER_OPEN, FINGER_OPEN, FINGER_OPEN, FINGER_OPEN, FINGER_OPEN);
}

void gestureFist() {
  setHandPose(FINGER_CLOSED, FINGER_CLOSED, FINGER_CLOSED, FINGER_CLOSED, FINGER_CLOSED);
}

void gesturePoint() {
  setHandPose(FINGER_CLOSED, FINGER_OPEN, FINGER_CLOSED, FINGER_CLOSED, FINGER_CLOSED);
}

void gestureWave() {
  gestureOpenHand();
  setArmPose(90, 55, 70, 90);
  for (int i = 0; i < 3; i++) {
    setArmPose(110, 55, 70, 70);
    setArmPose(70, 55, 70, 110);
  }
}

void handleGesture(String payload) {
  payload.trim();
  if (payload == "WAVE") {
    gestureWave();
  } else if (payload == "POINT") {
    gesturePoint();
  } else if (payload == "OPEN") {
    gestureOpenHand();
  } else if (payload == "FIST") {
    gestureFist();
  }
}

void setup() {
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() <= 0) return;

  incoming = Serial.readStringUntil('\n');
  incoming.trim();

  if (incoming == "HOME") {
    goHome();
  } else if (incoming.startsWith("ARM:")) {
    String payload = incoming.substring(4);
    int cursor = 0;
    int sr = nextValue(payload, cursor);
    int sl = nextValue(payload, cursor);
    int el = nextValue(payload, cursor);
    int wr = nextValue(payload, cursor);
    setArmPose(sr, sl, el, wr);
  } else if (incoming.startsWith("HAND:")) {
    String payload = incoming.substring(5);
    int cursor = 0;
    int f1 = nextValue(payload, cursor);
    int f2 = nextValue(payload, cursor);
    int f3 = nextValue(payload, cursor);
    int f4 = nextValue(payload, cursor);
    int f5 = nextValue(payload, cursor);
    setHandPose(f1, f2, f3, f4, f5);
  } else if (incoming.startsWith("RAW:")) {
    setRawPose(incoming.substring(4));
  } else if (incoming.startsWith("GESTURE:")) {
    handleGesture(incoming.substring(8));
  }
}
