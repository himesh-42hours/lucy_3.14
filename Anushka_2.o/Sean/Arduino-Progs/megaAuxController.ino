#include <Servo.h>

/*
  Head Mega (4 servos):
  - neck rotation
  - jaw
  - eyes up/down
  - eyelids up/down

  Serial commands:
    TALK:1 / TALK:0
    NOD:YES / NOD:NO
    NECK:<0-180>
    EYES:UP / EYES:DOWN / EYES:CENTER
    BLINK
    JAW:OPEN / JAW:CLOSE

  Update pin and angle constants to match your hardware.
*/

const uint8_t PIN_NECK = 35;
const uint8_t PIN_JAW = 34;
const uint8_t PIN_EYE_Y = 32;
const uint8_t PIN_EYELID = 22;

const int NECK_CENTER = 90;
const int NECK_MIN = 60;
const int NECK_MAX = 120;

const int JAW_CLOSED = 90;
const int JAW_OPEN = 120;
const uint16_t JAW_PERIOD_MS = 180;

const int EYE_CENTER = 90;
const int EYE_UP = 60;
const int EYE_DOWN = 120;

const int EYELID_OPEN = 90;
const int EYELID_CLOSED = 140;

const uint16_t BLINK_CLOSE_MS = 160;
const uint16_t BLINK_INTERVAL_IDLE_MS = 6000;
const uint16_t BLINK_INTERVAL_TALK_MS = 3200;

const uint16_t SACCADE_INTERVAL_MS = 900;
const uint16_t NECK_STEP_DELAY_MS = 140;

Servo neckServo;
Servo jawServo;
Servo eyeServo;
Servo eyelidServo;

String incoming;

bool talkActive = false;
bool jawIsOpen = false;

unsigned long jawNextAt = 0;
unsigned long blinkNextAt = 0;
unsigned long blinkPhaseAt = 0;
bool blinkInProgress = false;

unsigned long saccadeNextAt = 0;
uint8_t saccadeStep = 0;

int neckCurrent = NECK_CENTER;
int neckSeq[8];
uint8_t neckSeqLen = 0;
uint8_t neckSeqIndex = 0;
unsigned long neckNextAt = 0;
bool neckSeqActive = false;

void setNeck(int angle) {
  angle = constrain(angle, NECK_MIN, NECK_MAX);
  neckCurrent = angle;
  neckServo.write(angle);
}

void setJaw(bool open) {
  jawIsOpen = open;
  jawServo.write(open ? JAW_OPEN : JAW_CLOSED);
}

void setEyesCenter() {
  eyeServo.write(EYE_CENTER);
}

void setEyesUp() {
  eyeServo.write(EYE_UP);
}

void setEyesDown() {
  eyeServo.write(EYE_DOWN);
}

void openEyelids() {
  eyelidServo.write(EYELID_OPEN);
}

void closeEyelids() {
  eyelidServo.write(EYELID_CLOSED);
}

void startBlink(unsigned long now) {
  blinkInProgress = true;
  blinkPhaseAt = now;
  closeEyelids();
}

void updateBlink(unsigned long now) {
  if (blinkInProgress) {
    if (now - blinkPhaseAt >= BLINK_CLOSE_MS) {
      openEyelids();
      blinkInProgress = false;
      blinkNextAt = now + (talkActive ? BLINK_INTERVAL_TALK_MS : BLINK_INTERVAL_IDLE_MS);
    }
    return;
  }

  if (now >= blinkNextAt) {
    startBlink(now);
  }
}

void updateTalk(unsigned long now) {
  if (!talkActive) return;

  if (now >= jawNextAt) {
    setJaw(!jawIsOpen);
    jawNextAt = now + JAW_PERIOD_MS;
  }

  if (now >= saccadeNextAt) {
    switch (saccadeStep % 3) {
      case 0: setEyesCenter(); break;
      case 1: setEyesUp(); break;
      default: setEyesDown(); break;
    }
    saccadeStep++;
    saccadeNextAt = now + SACCADE_INTERVAL_MS;
  }
}

void startTalk(bool enable) {
  talkActive = enable;
  if (enable) {
    jawNextAt = millis();
    saccadeNextAt = millis() + 200;
    blinkNextAt = millis() + BLINK_INTERVAL_TALK_MS;
  } else {
    setJaw(false);
    setEyesCenter();
    blinkNextAt = millis() + BLINK_INTERVAL_IDLE_MS;
  }
}

void startNeckYes() {
  neckSeqLen = 5;
  neckSeq[0] = NECK_CENTER;
  neckSeq[1] = constrain(NECK_CENTER - 8, NECK_MIN, NECK_MAX);
  neckSeq[2] = NECK_CENTER;
  neckSeq[3] = constrain(NECK_CENTER - 8, NECK_MIN, NECK_MAX);
  neckSeq[4] = NECK_CENTER;
  neckSeqIndex = 0;
  neckSeqActive = true;
  neckNextAt = millis();
}

void startNeckNo() {
  neckSeqLen = 5;
  neckSeq[0] = constrain(NECK_CENTER - 18, NECK_MIN, NECK_MAX);
  neckSeq[1] = constrain(NECK_CENTER + 18, NECK_MIN, NECK_MAX);
  neckSeq[2] = constrain(NECK_CENTER - 18, NECK_MIN, NECK_MAX);
  neckSeq[3] = NECK_CENTER;
  neckSeq[4] = NECK_CENTER;
  neckSeqIndex = 0;
  neckSeqActive = true;
  neckNextAt = millis();
}

void updateNeckSequence(unsigned long now) {
  if (!neckSeqActive) return;
  if (now < neckNextAt) return;

  setNeck(neckSeq[neckSeqIndex]);
  neckSeqIndex++;
  if (neckSeqIndex >= neckSeqLen) {
    neckSeqActive = false;
  } else {
    neckNextAt = now + NECK_STEP_DELAY_MS;
  }
}

void handleEyesCommand(String payload) {
  payload.trim();
  if (payload == "UP") {
    setEyesUp();
  } else if (payload == "DOWN") {
    setEyesDown();
  } else {
    setEyesCenter();
  }
}

void handleJawCommand(String payload) {
  payload.trim();
  if (payload == "OPEN") {
    talkActive = false;
    setJaw(true);
  } else if (payload == "CLOSE") {
    talkActive = false;
    setJaw(false);
  }
}

void handleCommand(String cmd) {
  if (cmd.startsWith("TALK:")) {
    startTalk(cmd.substring(5).toInt() > 0);
    return;
  }
  if (cmd.startsWith("NOD:")) {
    String payload = cmd.substring(4);
    payload.trim();
    if (payload == "YES") {
      startNeckYes();
    } else if (payload == "NO") {
      startNeckNo();
    }
    return;
  }
  if (cmd.startsWith("NECK:")) {
    setNeck(cmd.substring(5).toInt());
    return;
  }
  if (cmd.startsWith("EYES:")) {
    handleEyesCommand(cmd.substring(5));
    return;
  }
  if (cmd == "BLINK") {
    startBlink(millis());
    return;
  }
  if (cmd.startsWith("JAW:")) {
    handleJawCommand(cmd.substring(4));
    return;
  }
}

void setup() {
  Serial.begin(9600);

  neckServo.attach(PIN_NECK);
  jawServo.attach(PIN_JAW);
  eyeServo.attach(PIN_EYE_Y);
  eyelidServo.attach(PIN_EYELID);

  setNeck(NECK_CENTER);
  setJaw(false);
  setEyesCenter();
  openEyelids();

  blinkNextAt = millis() + BLINK_INTERVAL_IDLE_MS;
}

void loop() {
  if (Serial.available() > 0) {
    incoming = Serial.readStringUntil('\n');
    incoming.trim();
    if (incoming.length() > 0) {
      handleCommand(incoming);
    }
  }

  unsigned long now = millis();
  updateTalk(now);
  updateBlink(now);
  updateNeckSequence(now);
}
