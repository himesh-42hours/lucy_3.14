#include <Servo.h>

/*
  Dual-arm controller for one Arduino Mega.

  Per arm layout:
  - 1 shoulder rotate servo
  - 2 shoulder lift servos working together
  - 2 elbow servos working together
  - 1 palm rotate servo
  - 5 finger servos

  Total: 11 servos per arm, 22 servos overall.

  Serial protocol:
    LARM:a,b,c,d,e,f
    RARM:a,b,c,d,e,f
    LHAND:f1,f2,f3,f4,f5
    RHAND:f1,f2,f3,f4,f5
    HOME
    PING

  Notes:
  - Update the pin arrays below to match your wiring.
  - Mirror/inversion can be tuned with *_REVERSE arrays.
*/

const uint8_t LEFT_ARM_PINS[6] = {2, 3, 4, 5, 6, 7};
const uint8_t RIGHT_ARM_PINS[6] = {8, 9, 10, 11, 12, 13};
const uint8_t LEFT_HAND_PINS[5] = {22, 23, 24, 25, 26};
const uint8_t RIGHT_HAND_PINS[5] = {27, 28, 29, 30, 31};

const bool LEFT_ARM_REVERSE[6] = {false, false, true, false, true, false};
const bool RIGHT_ARM_REVERSE[6] = {true, true, false, true, false, true};
const bool LEFT_HAND_REVERSE[5] = {true, true, true, true, true};
const bool RIGHT_HAND_REVERSE[5] = {false, false, false, false, false};

const int ARM_HOME[6] = {90, 90, 90, 90, 90, 90};
const int HAND_HOME[5] = {90, 90, 90, 90, 90};

Servo leftArm[6];
Servo rightArm[6];
Servo leftHand[5];
Servo rightHand[5];

int currentLeftArm[6] = {90, 90, 90, 90, 90, 90};
int currentRightArm[6] = {90, 90, 90, 90, 90, 90};
int currentLeftHand[5] = {90, 90, 90, 90, 90};
int currentRightHand[5] = {90, 90, 90, 90, 90};

String incoming;

int clampAngle(int value) {
  if (value < 0) return 0;
  if (value > 180) return 180;
  return value;
}

int parseNextValue(String &payload, int &cursor) {
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

void writeMirrored(Servo &servo, int angle, bool reverse) {
  servo.write(reverse ? 180 - angle : angle);
}

void moveSmooth(
  Servo *servos,
  int *currentValues,
  const bool *reverseMask,
  int *targets,
  int count,
  int delayMs
) {
  bool changed = true;
  while (changed) {
    changed = false;
    for (int i = 0; i < count; i++) {
      if (currentValues[i] < targets[i]) {
        currentValues[i]++;
        writeMirrored(servos[i], currentValues[i], reverseMask[i]);
        changed = true;
      } else if (currentValues[i] > targets[i]) {
        currentValues[i]--;
        writeMirrored(servos[i], currentValues[i], reverseMask[i]);
        changed = true;
      }
    }
    delay(delayMs);
  }
}

void handleServoGroup(
  Servo *servos,
  int *currentValues,
  const bool *reverseMask,
  int count,
  String payload
) {
  int targets[6];
  int cursor = 0;
  for (int i = 0; i < count; i++) {
    targets[i] = parseNextValue(payload, cursor);
  }
  moveSmooth(servos, currentValues, reverseMask, targets, count, 10);
}

void goHome() {
  int armTargets[6];
  int handTargets[5];
  for (int i = 0; i < 6; i++) armTargets[i] = ARM_HOME[i];
  for (int i = 0; i < 5; i++) handTargets[i] = HAND_HOME[i];

  moveSmooth(leftArm, currentLeftArm, LEFT_ARM_REVERSE, armTargets, 6, 10);
  moveSmooth(rightArm, currentRightArm, RIGHT_ARM_REVERSE, armTargets, 6, 10);
  moveSmooth(leftHand, currentLeftHand, LEFT_HAND_REVERSE, handTargets, 5, 10);
  moveSmooth(rightHand, currentRightHand, RIGHT_HAND_REVERSE, handTargets, 5, 10);
}

void attachGroup(Servo *servos, const uint8_t *pins, int *currentValues, const bool *reverseMask, int count) {
  for (int i = 0; i < count; i++) {
    servos[i].attach(pins[i]);
    writeMirrored(servos[i], currentValues[i], reverseMask[i]);
    delay(25);
  }
}

void setup() {
  Serial.begin(9600);
  attachGroup(leftArm, LEFT_ARM_PINS, currentLeftArm, LEFT_ARM_REVERSE, 6);
  attachGroup(rightArm, RIGHT_ARM_PINS, currentRightArm, RIGHT_ARM_REVERSE, 6);
  attachGroup(leftHand, LEFT_HAND_PINS, currentLeftHand, LEFT_HAND_REVERSE, 5);
  attachGroup(rightHand, RIGHT_HAND_PINS, currentRightHand, RIGHT_HAND_REVERSE, 5);
  goHome();
  Serial.println("DUAL_ARM_READY");
}

void loop() {
  if (Serial.available() <= 0) {
    return;
  }

  incoming = Serial.readStringUntil('\n');
  incoming.trim();

  if (incoming == "PING") {
    Serial.println("PONG");
    return;
  }

  if (incoming == "HOME") {
    goHome();
    Serial.println("OK:HOME");
    return;
  }

  if (incoming.startsWith("LARM:")) {
    handleServoGroup(leftArm, currentLeftArm, LEFT_ARM_REVERSE, 6, incoming.substring(5));
    Serial.println("OK:LARM");
  } else if (incoming.startsWith("RARM:")) {
    handleServoGroup(rightArm, currentRightArm, RIGHT_ARM_REVERSE, 6, incoming.substring(5));
    Serial.println("OK:RARM");
  } else if (incoming.startsWith("LHAND:")) {
    handleServoGroup(leftHand, currentLeftHand, LEFT_HAND_REVERSE, 5, incoming.substring(6));
    Serial.println("OK:LHAND");
  } else if (incoming.startsWith("RHAND:")) {
    handleServoGroup(rightHand, currentRightHand, RIGHT_HAND_REVERSE, 5, incoming.substring(6));
    Serial.println("OK:RHAND");
  } else {
    Serial.print("ERR:UNKNOWN:");
    Serial.println(incoming);
  }
}
