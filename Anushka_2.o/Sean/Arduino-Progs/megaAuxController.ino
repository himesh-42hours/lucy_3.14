#include <CytronMotorDriver.h>
#include <Servo.h>

/*
  Shared auxiliary Mega for:
  - jaw
  - eye mechanism
  - neck
  - wheel base

  Python sends line-based commands in these formats:

  J:<seconds>
  E:<gesture_id>
  N:<angle>
  R:<direction@seconds>

  Update the pin constants below to match your actual wiring.
*/

const int JAW_PIN = 34;
const int NECK_PIN = 35;
const int TOP_LEFT_EYELID_PIN = 22;
const int BOTTOM_LEFT_EYELID_PIN = 24;
const int TOP_RIGHT_EYELID_PIN = 26;
const int BOTTOM_RIGHT_EYELID_PIN = 28;
const int EYE_Y_PIN = 32;
const int EYE_X_PIN = 30;

const int JAW_LOWER_LIMIT = 65;
const int JAW_UPPER_LIMIT = 100;
const int JAW_DELAY_MS = 180;

CytronMD leftMotor(PWM_DIR, 3, 4);
CytronMD rightMotor(PWM_DIR, 6, 7);

Servo jawServo;
Servo neckServo;
Servo topLeftEyelid;
Servo bottomLeftEyelid;
Servo topRightEyelid;
Servo bottomRightEyelid;
Servo eyeY;
Servo eyeX;

String incoming;
int currentNeck = 90;
bool shouldBlink = true;
unsigned long lastBlinkAt = 0;

void closeEye() {
  topLeftEyelid.write(145);
  bottomLeftEyelid.write(40);
  topRightEyelid.write(35);
  bottomRightEyelid.write(140);
}

void openEye() {
  topLeftEyelid.write(95);
  bottomLeftEyelid.write(90);
  topRightEyelid.write(85);
  bottomRightEyelid.write(90);
}

void eyeCenter() {
  eyeX.write(90);
  eyeY.write(90);
}

void eyeLeft() {
  eyeX.write(30);
}

void eyeRight() {
  eyeX.write(140);
}

void lookUp() {
  eyeY.write(50);
}

void lookDown() {
  eyeY.write(130);
}

void startupEyeMotion() {
  eyeX.write(60);
  delay(280);
  eyeY.write(80);
  delay(280);
  eyeX.write(120);
  delay(280);
  eyeY.write(140);
  delay(280);
  eyeCenter();
  delay(250);
  closeEye();
  delay(360);
  openEye();
}

void moveNeck(int target) {
  target = constrain(target, 70, 140);
  while (currentNeck != target) {
    if (currentNeck < target) {
      currentNeck++;
    } else {
      currentNeck--;
    }
    neckServo.write(currentNeck);
    delay(10);
  }
}

void runJawForSeconds(int secondsToRun) {
  unsigned long startAt = millis();
  while ((millis() - startAt) < (unsigned long) secondsToRun * 1000UL) {
    jawServo.write(JAW_LOWER_LIMIT);
    delay(JAW_DELAY_MS);
    jawServo.write(JAW_UPPER_LIMIT);
    delay(JAW_DELAY_MS);
  }
}

void runEyeGesture(int gesture) {
  if (gesture == 0) {
    startupEyeMotion();
    shouldBlink = false;
  } else if (gesture == 1) {
    eyeLeft();
    shouldBlink = true;
  } else if (gesture == 2) {
    eyeRight();
    shouldBlink = true;
  } else if (gesture == 3) {
    eyeCenter();
    shouldBlink = true;
  } else if (gesture == 4) {
    lookUp();
    shouldBlink = true;
  } else if (gesture == 5) {
    lookDown();
    shouldBlink = true;
  } else if (gesture == 6) {
    closeEye();
    shouldBlink = false;
  } else if (gesture == 7) {
    openEye();
    shouldBlink = false;
  } else if (gesture == 8) {
    closeEye();
    delay(800);
    eyeCenter();
    openEye();
    shouldBlink = false;
  } else if (gesture == -2) {
    eyeCenter();
    openEye();
    shouldBlink = true;
  }
  lastBlinkAt = millis();
}

void stopBase() {
  leftMotor.setSpeed(0);
  rightMotor.setSpeed(0);
}

void runBaseCommand(String payload) {
  char direction = payload.charAt(0);
  int sep = payload.indexOf('@');
  if (sep < 0) {
    return;
  }
  float secondsToRun = payload.substring(sep + 1).toFloat();
  int speed = 60;

  if (direction == 'f') {
    leftMotor.setSpeed(speed);
    rightMotor.setSpeed(speed);
  } else if (direction == 'b') {
    leftMotor.setSpeed(-speed);
    rightMotor.setSpeed(-speed);
  } else if (direction == 'l') {
    leftMotor.setSpeed(-speed);
    rightMotor.setSpeed(speed);
  } else if (direction == 'r') {
    leftMotor.setSpeed(speed);
    rightMotor.setSpeed(-speed);
  } else {
    stopBase();
    return;
  }

  delay((int) (secondsToRun * 1000.0f));
  stopBase();
}

void setup() {
  Serial.begin(9600);

  jawServo.attach(JAW_PIN);
  neckServo.attach(NECK_PIN);
  topLeftEyelid.attach(TOP_LEFT_EYELID_PIN);
  bottomLeftEyelid.attach(BOTTOM_LEFT_EYELID_PIN);
  topRightEyelid.attach(TOP_RIGHT_EYELID_PIN);
  bottomRightEyelid.attach(BOTTOM_RIGHT_EYELID_PIN);
  eyeY.attach(EYE_Y_PIN);
  eyeX.attach(EYE_X_PIN);

  jawServo.write(JAW_UPPER_LIMIT);
  neckServo.write(currentNeck);
  openEye();
  eyeCenter();
  lastBlinkAt = millis();
}

void loop() {
  if (Serial.available() > 0) {
    incoming = Serial.readStringUntil('\n');
    incoming.trim();

    if (incoming.startsWith("J:")) {
      runJawForSeconds(incoming.substring(2).toInt());
    } else if (incoming.startsWith("E:")) {
      runEyeGesture(incoming.substring(2).toInt());
    } else if (incoming.startsWith("N:")) {
      moveNeck(incoming.substring(2).toInt());
    } else if (incoming.startsWith("R:")) {
      runBaseCommand(incoming.substring(2));
    }
  }

  if (shouldBlink && (millis() - lastBlinkAt) >= 6000) {
    closeEye();
    delay(250);
    openEye();
    lastBlinkAt = millis();
  }
}
