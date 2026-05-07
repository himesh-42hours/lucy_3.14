#include <Servo.h>

/*
  Flash one copy to the left-arm Mega and one copy to the right-arm Mega.
  The Python runtime now sends commands in these formats:

  ARM:a1,a2,a3,a4
  HAND:f1,f2,f3,f4,f5

  Update the pin arrays below to match your actual wiring on each Mega.
*/

const int ARM_SERVO_PINS[4] = {2, 3, 4, 5};
const int FINGER_SERVO_PINS[5] = {6, 7, 8, 9, 10};

Servo armServos[4];
Servo fingerServos[5];

int currentArm[4] = {90, 90, 90, 90};
int currentFingers[5] = {90, 90, 90, 90, 90};

String incoming;

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
  return constrain(token.toInt(), 0, 180);
}

void moveSmooth(Servo *servos, int *currentValues, int *targets, int count, int delayMs) {
  bool changed = true;
  while (changed) {
    changed = false;
    for (int i = 0; i < count; i++) {
      if (currentValues[i] < targets[i]) {
        currentValues[i]++;
        servos[i].write(currentValues[i]);
        changed = true;
      } else if (currentValues[i] > targets[i]) {
        currentValues[i]--;
        servos[i].write(currentValues[i]);
        changed = true;
      }
    }
    delay(delayMs);
  }
}

void handleArm(String payload) {
  int targets[4];
  int cursor = 0;
  for (int i = 0; i < 4; i++) {
    targets[i] = nextValue(payload, cursor);
  }
  moveSmooth(armServos, currentArm, targets, 4, 12);
}

void handleHand(String payload) {
  int targets[5];
  int cursor = 0;
  for (int i = 0; i < 5; i++) {
    targets[i] = nextValue(payload, cursor);
  }
  moveSmooth(fingerServos, currentFingers, targets, 5, 12);
}

void doJaaduTona() {
  int spellA[5] = {170, 90, 55, 55, 55};
  int spellB[5] = {120, 40, 130, 40, 130};
  moveSmooth(fingerServos, currentFingers, spellA, 5, 10);
  delay(250);
  moveSmooth(fingerServos, currentFingers, spellB, 5, 10);
  delay(250);
  moveSmooth(fingerServos, currentFingers, spellA, 5, 10);
}

void setup() {
  Serial.begin(9600);

  for (int i = 0; i < 4; i++) {
    armServos[i].attach(ARM_SERVO_PINS[i]);
    armServos[i].write(currentArm[i]);
  }

  for (int i = 0; i < 5; i++) {
    fingerServos[i].attach(FINGER_SERVO_PINS[i]);
    fingerServos[i].write(currentFingers[i]);
  }
}

void loop() {
  if (Serial.available() <= 0) {
    return;
  }

  incoming = Serial.readStringUntil('\n');
  incoming.trim();

  if (incoming.startsWith("ARM:")) {
    handleArm(incoming.substring(4));
  } else if (incoming.startsWith("HAND:")) {
    handleHand(incoming.substring(5));
  } else if (incoming == "SPECIAL:JAADUTONA") {
    doJaaduTona();
  }
}
