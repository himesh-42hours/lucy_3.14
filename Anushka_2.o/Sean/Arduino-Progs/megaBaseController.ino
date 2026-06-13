#include <CytronMotorDriver.h>

/*
  Base Mega (2 motors with Cytron driver).

  Serial commands:
    BASE:F,120,1000   (dir F/B/L/R, speed 0-255, duration ms; 0 = run until STOP)
    STOP
    GESTURE:SPIN

  Update motor pins and any speed limits below.
*/

const uint8_t LEFT_PWM_PIN = 3;
const uint8_t LEFT_DIR_PIN = 4;
const uint8_t RIGHT_PWM_PIN = 6;
const uint8_t RIGHT_DIR_PIN = 7;

const int MAX_SPEED = 200;

CytronMD leftMotor(PWM_DIR, LEFT_PWM_PIN, LEFT_DIR_PIN);
CytronMD rightMotor(PWM_DIR, RIGHT_PWM_PIN, RIGHT_DIR_PIN);

String incoming;

struct MotionState {
  bool active;
  int leftSpeed;
  int rightSpeed;
  unsigned long stopAt;
};

MotionState motion = {false, 0, 0, 0};

int clampSpeed(int value) {
  if (value < -MAX_SPEED) return -MAX_SPEED;
  if (value > MAX_SPEED) return MAX_SPEED;
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
  return token.toInt();
}

void applySpeed(int left, int right) {
  leftMotor.setSpeed(clampSpeed(left));
  rightMotor.setSpeed(clampSpeed(right));
}

void stopBase() {
  motion.active = false;
  motion.stopAt = 0;
  applySpeed(0, 0);
}

void startMotion(int left, int right, unsigned long durationMs) {
  motion.active = true;
  motion.leftSpeed = left;
  motion.rightSpeed = right;
  motion.stopAt = (durationMs == 0) ? 0 : millis() + durationMs;
  applySpeed(left, right);
}

void updateMotion() {
  if (!motion.active) return;
  if (motion.stopAt != 0 && millis() >= motion.stopAt) {
    stopBase();
  }
}

void handleBaseCommand(String payload) {
  int comma = payload.indexOf(',');
  if (comma < 0) return;

  char dir = payload.charAt(0);
  int cursor = comma + 1;
  int speed = clampSpeed(nextValue(payload, cursor));
  unsigned long durationMs = (unsigned long) nextValue(payload, cursor);

  if (dir == 'F') {
    startMotion(speed, speed, durationMs);
  } else if (dir == 'B') {
    startMotion(-speed, -speed, durationMs);
  } else if (dir == 'L') {
    startMotion(-speed, speed, durationMs);
  } else if (dir == 'R') {
    startMotion(speed, -speed, durationMs);
  }
}

void handleGesture(String payload) {
  payload.trim();
  if (payload == "SPIN") {
    startMotion(160, -160, 900);
  }
}

void setup() {
  Serial.begin(9600);
  stopBase();
}

void loop() {
  if (Serial.available() > 0) {
    incoming = Serial.readStringUntil('\n');
    incoming.trim();

    if (incoming.startsWith("BASE:")) {
      handleBaseCommand(incoming.substring(5));
    } else if (incoming == "STOP") {
      stopBase();
    } else if (incoming.startsWith("GESTURE:")) {
      handleGesture(incoming.substring(8));
    }
  }

  updateMotion();
}
