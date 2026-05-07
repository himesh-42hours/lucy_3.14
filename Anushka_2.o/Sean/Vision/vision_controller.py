from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
VISION_EF_FILE = SEAN_ROOT / "Vision" / "visionEF.txt"
VISION_WS_FILE = SEAN_ROOT / "Vision" / "visionWS.txt"
FACES_DIR = SEAN_ROOT / "Vision" / "faces"
HEAR_COM_FILE = SEAN_ROOT / "Hearing" / "hearCom.txt"
CURRENTLY_PRESENT_FILE = SEAN_ROOT / "Vision" / "currentlyPresent.txt"
LAST_SEEN_FILE = SEAN_ROOT / "Vision" / "lastSeenMe.txt"
MONITOR_WS_FILE = SEAN_ROOT / "Monitor" / "monitorWS.txt"
REMEMBER_WAV = SEAN_ROOT / "Resources" / "RememberHmm.wav"


def _vision_stage(message: str) -> None:
    try:
        with open(VISION_EF_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"{message}\n")
    except Exception:
        pass


try:
    _vision_stage("vision: import block start")
    import sys
    import time
    import platform
    import traceback
    from playsound import playsound
    import serial
    for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    from anushka_runtime.config import CAMERA_INDEX, CAMERA_NAME_HINT, CAMERA_SOURCE
    from Speech.essentialFunctions import *
    from Hearing.essentialFunctions import *
    from runtime_helpers import *
    _vision_stage("vision: core helpers imported")
    import cv2
    from cvzone.HandTrackingModule import HandDetector
    #// from cvzone.ClassificationModule import Classifier
    from cvzone.FaceDetectionModule import FaceDetector
    from cvzone.FaceMeshModule import FaceMeshDetector
    from cvzone.PoseModule import PoseDetector
    import numpy as np
    import math
    import face_recognition
    import os
    import numpy as np
    _vision_stage("vision: vision libraries imported")

except Exception as exc:
    import traceback

    error_message = f"Error importing modules for vision: {exc!s}\n{traceback.format_exc()}\n"
    visionEF= open(VISION_EF_FILE, 'a')
    visionEF.write(error_message)
    visionEF.close()
    try:
        sys.stderr.write(f"[vision] {error_message}")
        sys.stderr.flush()
    except Exception:
        pass
    exit()


path= str(FACES_DIR)
images= []
classNames= []
myList= os.listdir(path)
_vision_stage(f"vision: loading {len(myList)} known face image(s)")
fw = 800
fh = 600
imgSize = 300

def allSame(lst):
    b = True
    for i in range(len(lst) - 1):
        if lst[i] != lst[i + 1]:
            return False
    return True


for cls in myList:
    img= cv2.imread(f"{path}/{cls}")
    images.append(img)
    classNames.append(os.path.splitext(cls)[0])

def findEncodings(images):
    encodeList= []
    for img in images:
        img= cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode= face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList

encodeListKnown= findEncodings(images)
_vision_stage(f"vision: encoded {len(encodeListKnown)} known face(s)")
print("Encoding Complete :)")

try:
    if platform.system() == "Windows":
        if isinstance(CAMERA_SOURCE, int):
            cam=cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_DSHOW)
        else:
            cam=cv2.VideoCapture(CAMERA_SOURCE)
    else:
        if isinstance(CAMERA_SOURCE, int) and hasattr(cv2, "CAP_V4L2"):
            cam=cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_V4L2)
        else:
            cam=cv2.VideoCapture(CAMERA_SOURCE)
    if not cam or not cam.isOpened():
        raise RuntimeError(
            f"Camera source {CAMERA_SOURCE!r} did not open"
            + (f" (hint: {CAMERA_NAME_HINT})" if CAMERA_NAME_HINT else "")
        )
    try:
        cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    except Exception:
        pass
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, fw)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, fh)
    _vision_stage(f"vision: camera {CAMERA_SOURCE!r} opened")
except Exception as exc:
    visionEF= open(VISION_EF_FILE, 'a')
    visionEF.write(f"Error opening camera for vision module: {exc!s}\n")
    visionEF.close()
    exit()

detector = None
myFaceDetector = None
#// classifier = Classifier("Vision/model/keras_model.h5", "Vision/model/labels.txt")

visionWS= open(VISION_WS_FILE, 'r')
lastRead= visionWS.read()
lastFace= "Hi"

mode= 0

_vision_stage("vision: startup complete")

visionEF= open(VISION_EF_FILE, 'a')
visionEF.write("1")
visionEF.close()

last5Faces= []
last15Embeddings= []
shouldCheck = True
shouldRotate= True
angles= []
prevTime= time.time()
metImportantPerson= False
GARDAN_MOVEMENT_TIME= 2

psDetector= None
fmDetector= None


def get_face_detector():
    global myFaceDetector
    if myFaceDetector is None:
        myFaceDetector = FaceDetector(0.6)
    return myFaceDetector


def get_hand_detector():
    global detector
    if detector is None:
        detector = HandDetector(maxHands=2)
    return detector


def get_pose_detector():
    global psDetector
    if psDetector is None:
        psDetector = PoseDetector()
    return psDetector


def get_face_mesh_detector():
    global fmDetector
    if fmDetector is None:
        fmDetector = FaceMeshDetector(maxFaces=1)
    return fmDetector


def read_frame(max_attempts=3, delay_seconds=0.08):
    for _ in range(max_attempts):
        ret, frame = cam.read()
        if ret and frame is not None:
            return True, frame
        time.sleep(delay_seconds)
    return False, None


ok, _frame = read_frame(max_attempts=2, delay_seconds=0.15)
if not ok:
    visionEF= open(VISION_EF_FILE, 'a')
    visionEF.write(f"Error opening camera for vision module: camera {CAMERA_SOURCE!r} opened but no frames were received\n")
    visionEF.close()
    exit()

while True:
        
    newRead= visionWS.readline()
    if len(newRead) != 0:
        mode= newRead.strip()
        mode= int(mode)
        print("New mode here: ", mode)
    
    if mode == -1:
        #todo Remove these try in real-time testing
        try:
            cv2.destroyWindow("White")
        except:
            pass
        try:
            cv2.destroyWindow("Headshot")
        except:
            pass
        try:
            cv2.destroyWindow("Window")
        except:
            pass
        break
    
    if mode == 0:
        #todo Remove these try in real-time testing
        try:
            cv2.destroyWindow("White")
        except:
            pass
        try:
            cv2.destroyWindow("Headshot")
        except:
            pass
        try:
            cv2.destroyWindow("Window")
        except:
            pass

        continue

    elif mode == 1:   #Recognition and neck movement
        #todo Remove these try in real-time testing
        try:
            cv2.destroyWindow("White")
        except:
            pass
        try:
            cv2.destroyWindow("Headshot")
        except:
            pass
        
        ret, img = read_frame()
        if not ret:
            errFile= open(VISION_EF_FILE, 'a')
            errFile.write("Vision warning: no image acquired during recognition frame read; retrying\n")
            errFile.close()
            time.sleep(0.2)
            continue

        newTime= time.time()
        img, bboxs = get_face_detector().findFaces(img, draw= False)
        kk= img.copy()
        tt, battle= get_face_detector().findFaces(kk, draw= True)
        if not bboxs:
            shouldCheck= True       #should check for new faces when there were no face last time
            shouldRotate= True

        if len(bboxs) > 2 and shouldCheck:
            
            pauseHearing()
            hearCom= open(HEAR_COM_FILE, 'r')
            while True:
                kkk= hearCom.readline().strip()
                if kkk=="1":
                    break
            hearCom.close()

            print("Nice to meet you new person")
            writeToHaath("6")   #Hello guesture
            speak("Hello there! Nice to meet you all. It is always a delight to interact with such a vibrant group of individuals. If there's anything I can assist you with, please don't hesitate to ask.")

            playHearing()

            shouldCheck= False

        elif bboxs and shouldCheck and int(bboxs[0]["score"][0]*100)>=94:
            """
            #? BBox structure
            bboxInfo - "id","bbox","score","center"
            center = bboxs[0]["center"]
            cv2.circle(img, center, 5, (255, 0, 255), cv2.FILLED)
            """
            
            x1= bboxs[0]["bbox"][0]
            y1= bboxs[0]["bbox"][1]
            x2= x1+ bboxs[0]["bbox"][2]
            y2= y1+ bboxs[0]["bbox"][3]
            x1= x1-40
            if x1<=0:
                x1= 0
            y1= y1- 40
            if y1<=0:
                y1= 0
            x2= x2+ 40
            if x2>=800:
                x2= 800
            y2= y2+ 40
            if y2>=600:
                y2= 600
            
            mu= img[y1:y2, x1:x2]
            mu= cv2.cvtColor(mu, cv2.COLOR_BGR2RGB)
            
            #? y= (6*x + 3900)/70
            
            try:
                """
                'mu'= Crop face of person in camera.
                'muEncodings' hold encoding of that muh, 
                if person is recognized, special wish and add to last5faces
                else: normal hi
                """
                muEncodings= face_recognition.face_encodings(mu)[0]
                matches= face_recognition.compare_faces(encodeListKnown, muEncodings, 0.48)
                faceDis= face_recognition.face_distance(encodeListKnown, muEncodings)
                matchIndex= np.argmin(faceDis)

                if matches[matchIndex] and faceDis[matchIndex] <= 0.48:
                    nameToWrite= classNames[matchIndex]
                    if "father" in str(nameToWrite).lower():
                        nameToWrite= "Himesh Vijay"
                    peopleFile= open(CURRENTLY_PRESENT_FILE, 'w')
                    people= peopleFile.write(nameToWrite)
                    peopleFile.close()
                elif 0.48 < faceDis[matchIndex] <= 0.52:
                    nameToWrite= classNames[matchIndex]
                    if "father" in str(nameToWrite).lower():
                        nameToWrite= "Himesh Vijay"
                    peopleFile= open(CURRENTLY_PRESENT_FILE, 'w')
                    people= peopleFile.write(f"someone like {nameToWrite}")
                    peopleFile.close()
                else:
                    peopleFile= open(CURRENTLY_PRESENT_FILE, 'w')
                    people= peopleFile.write("none")
                    peopleFile.close()

                if matches[matchIndex]:
                    name= classNames[matchIndex]
                    if name not in last5Faces:
                        if len(last5Faces)>=5:
                            last5Faces.pop(0)
                        last5Faces.append(name)
                        # print(last5Faces)
                        print("Hello", name)    # ADD GREETING MECHANISM
                        pauseHearing()
                        hearCom= open(HEAR_COM_FILE, 'r')
                        while True:
                            kkk= hearCom.readline().strip()
                            if kkk=="1":
                                break
                        hearCom.close()
                        if name == "Father":
                            todaysDate= datetime.datetime.now()
                            print("Entered inside")

                            lastSeenFile= open(LAST_SEEN_FILE, 'r')
                            lastSeenDate= lastSeenFile.read()
                            lastSeenFile.close()
                            my_time= datetime.time()
                            lastSeenPoora= datetime.datetime.combine(datetime.datetime.strptime(lastSeenDate,"%d-%m-%Y"), my_time)
                            print(lastSeenPoora)

                            timeDelta= todaysDate - lastSeenPoora
                            print(str(timeDelta))
                            if timeDelta.days > 30:
                                writeToHaath("2")
                                speak("I missed you so much sire ")

                            else:
                                writeToHaath("3")    #Shake hand gesture
                                speak("Hello. Nice to meet you Himesh Vijay")
                            
                            #Last seen file update

                            lastSeenFile= open(LAST_SEEN_FILE, 'w')
                            lastSeenDate= lastSeenFile.write(todaysDate.strftime("%d-%m-%Y"))
                            lastSeenFile.close()

                            # To monitoring system
                            moniWS= open(MONITOR_WS_FILE, 'a')
                            moniWS.write("LastSeen- "+todaysDate.strftime("%d-%m-%Y"))
                            moniWS.close()
                        
                        elif name.strip() in ["Dr_Manoj_Goyal"]: #Special known people
                            writeToHaath("3")    #Shake hand gesture
                            speak("Hello. Nice to meet you " + name)
                        else:   #other known people
                            writeToHaath("12")    ##Jai hind gesture
                            speak("Jaye heend " + name)

                        #region Special Person
                        #todo Here
                        # elif (not metImportantPerson) and "yogi" in name.lower():
                        #     metImportantPerson= True
                        #     writeToHaath("12")    ##Jai hind gesture
                        #     speak("Pruhnaum Maanee-yeah mukhya muntri Yogi uhditya nath ji")

                        # elif name.strip() in ["Dr_Manoj_Goyal"]: #Special known people
                        #     writeToHaath("3")    #Shake hand gesture
                        #     speak("Hello. Nice to meet you " + name)
                        # else:   #other known people
                        #     if "yogi" in name:
                        #         print("Fir se yogi ji")
                        #         pass
                        #     else:
                        #         writeToHaath("12")    ##Jai hind gesture
                        #         speak("Pruhnaum " + name)
                        #endregion
                        
                        playHearing()
                else:
                    if len(last15Embeddings) == 0:
                        pauseHearing()
                        hearCom= open(HEAR_COM_FILE, 'r')
                        while True:
                            kkk= hearCom.readline().strip()
                            if kkk=="1":
                                break
                        hearCom.close()
                        last15Embeddings.append(muEncodings)
                        print("Nice to meet you new person")
                        writeToHaath("6")   #Hello guesture
                        speak("Hello. Nice to meet you.")
                        playHearing()
                        continue
                    unknownWaliMatches= face_recognition.compare_faces(last15Embeddings, muEncodings, 0.48)
                    unknownWalafaceDis= face_recognition.face_distance(last15Embeddings, muEncodings)
                    unknownWalaIndex= np.argmin(unknownWalafaceDis)
                    if not unknownWaliMatches[unknownWalaIndex]:
                        #bot will remember unknown faces now
                        if len(last15Embeddings) >= 15:
                            last15Embeddings.pop(0)
                        last15Embeddings.append(muEncodings)
                        pauseHearing()
                        hearCom= open(HEAR_COM_FILE, 'r')
                        while True:
                            kkk= hearCom.readline().strip()
                            if kkk=="1":
                                break
                        hearCom.close()
                        writeToHaath("6")   #Hello guesture
                        speak("Hello. Nice to meet you.")
                        print("Nice to meet you new person")
                        playHearing()
                    
                #todo: Remove imshows
                # cv2.imshow("Muh", mu)
            except:
                pass
            
            shouldCheck= False
        
        if len(bboxs) > 1:
            GARDAN_MOVEMENT_TIME= 5.0
        else:
            GARDAN_MOVEMENT_TIME= 2.0

        if bboxs and (newTime-prevTime >= GARDAN_MOVEMENT_TIME or shouldRotate) and int(bboxs[0]["score"][0]*100)>= 90:
            angles= []
            for i in range(len(bboxs)):
                xplace = bboxs[i]["center"][0]
                yplace= int(round((6*xplace + 3900)/70))
                angles.append(yplace)
            print(angles)
            servoAngle= retOutOf(angles)

            # try:
            #     gardan.write(str(servoAngle).encode())
            # except:
            #     monitorWS= open(MONITOR_WS_FILE, 'a')
            #     monitorWS.write("Error- [NON Fatal] The gardan module has stopped working")
            #     monitorWS.close()

            prevTime= newTime
            shouldRotate= False
            
        #todo: Remove imshows
        # cv2.imshow("Image", tt)

    elif mode==2:   #Headshot

        #Agar reco chalra hai to use abnd kardo
        #todo Remove these try in real-time testing
        try:
            cv2.destroyWindow("Window")
        except:
            pass
        try:
            cv2.destroyWindow("White")
        except:
            pass
        
        #todo: Remove imshows
        # cv2.imshow("Headshot", img)
        hearCom= open(HEAR_COM_FILE, 'r')
        kkk= hearCom.read()
        pauseHearing()

        try:
            playsound(str(REMEMBER_WAV))
        except:
            pass
        
        print("Hearing putting to stop")

        while True:
            kkk= hearCom.readline().strip()
            if len(kkk)>1:
                print(kkk)
            if kkk=="1":
                break
        hearCom.close()
        speak("Sure. I will be needing a clean photo here. Please stand still for a second.")
        print("Hearing has now been stopped by vision") #REMOVE IN FINAL EDITION
        time.sleep(3)

        #todo ADD EYE CAPTURE GESTURE
        photoSession= 0
        photoSuccess= False
        while photoSession<3:
            try:
                newRet, newImg= read_frame(max_attempts=5, delay_seconds=0.15)
                nayiImageKiEncodings= face_recognition.face_encodings(newImg)[0]
                photoSession=3
                photoSuccess= True
            except:
                speak("Uhh ohh? The photo is a bit blurry. Let me take another one")
                time.sleep(2)
                photoSession+=1
            
        if photoSuccess:
            name= ""
            speak("Done. Your good name, please?")
            name= str(s2t())
            if name == "None":
                speak("Sorry I couldn't get the name. Asking one more time. Your good name, please?")
                name= str(s2t())
                if name == "None":
                    speak("Sorry I couldn't get your name again. Abandoning the process.")
                    mode= 1
                    continue

            print("Great. I will remember you as "+name)
            speak("Great. I will remember you as "+name)
            img_name = str(FACES_DIR / f"{name}.jpg")
            cv2.imwrite(img_name, newImg)
            print(f"{img_name} written!")

            speak("Re-encoding all known faces, just a second.")
            print("Encoding available faces...")
            
            try:
                images= []
                classNames= []
                myList= os.listdir(path)
                for cls in myList:
                    Listimg= cv2.imread(f"{path}/{cls}")
                    images.append(Listimg)
                    classNames.append(os.path.splitext(cls)[0])
                encodeListKnown= findEncodings(images)   
            except:
                monitorWS= open(MONITOR_WS_FILE, 'a')
                monitorWS.write(f"Error- That unknown error from Remember me functionality that I never expect. {name}'s photo was not saved to the database.")
                monitorWS.close()
            
            monitorWS= open(MONITOR_WS_FILE, 'a')
            monitorWS.write(f"Log- {name}'s photo got saved to database")
            monitorWS.close()
            speak("Encoding Completed successfully")
        else:
            speak("You are our special guest. I will always remember you.") #Only flatterring
            writeToHaath("22")

        playHearing()
        mode= 1
            
    elif mode == 3: #ISL
        try:
            cv2.destroyWindow("Window")
        except:
            pass
        try:
            cv2.destroyWindow("Headshot")
        except:
            pass
            
        lastThree = [0]
        hands, img = get_hand_detector().findHands(img, draw=False)
        # print(len(hands))
        if len(hands) == 0:
            continue

        try:
            if len(hands) == 1:
                h = hands[0]
                hx, hy, hw, hh = h['bbox']

                hx -= 20
                hw += 40
                hh += 20
                hy -= 20

                if hx < 0:
                    hx = 0
                if hw > hw:
                    hw = fw
                if hy < 0:
                    hy = 0
                if hh > fh:
                    hh = fh

                imgWhite = np.ones((imgSize, imgSize, 3), np.uint8) * 255
                imgCrop = img[hy:hy + hh, hx:hx + hw]
                imgCropShape = imgCrop.shape

                aspectRatio = hh / hw

                if aspectRatio > 1:
                    k = imgSize / hh
                    wCal = math.ceil(k * hw)
                    imgResize = cv2.resize(imgCrop, (wCal, imgSize))
                    imgResizeShape = imgResize.shape
                    wGap = math.ceil((imgSize - wCal) / 2)
                    imgWhite[:, wGap:wCal + wGap] = imgResize


            else:
                k = imgSize / hw
                hCal = math.ceil(k * hh)
                imgResize = cv2.resize(imgCrop, (imgSize, hCal))
                imgResizeShape = imgResize.shape
                hGap = math.ceil((imgSize - hCal) / 2)
                imgWhite[hGap:hCal + hGap, :] = imgResize

                #ISE NHI KARNA # cv2.imshow("Cropped", imgCrop)  
                prediction, index = classifier.getPrediction(imgWhite)
                if lastThree[len(lastThree) - 1] == index:
                    lastThree.append(index)
                    if allSame(lastThree) and len(lastThree) == 3:
                        speak(index)
                        lastThree = [index]
                else:
                    lastThree = [index]
                # print(prediction, index)

                # cv2.imshow("White", imgWhite)
                # cv2.rectangle(img, (hx,hy), (hx+hw, hy+hh), (0,0,0), 2)

                if len(hands) == 2:
                    h1 = hands[0]
                    h2 = hands[1]
                    h1x, h1y, h1w, h1h = h1['bbox']
                    h2x, h2y, h2w, h2h = h2['bbox']

                    # print("left : ", h1x, h1y, h1w, h1h)
                    # ik= cv2.putText(img, ".", (h1x, h1y), cv2.FONT_HERSHEY_COMPLEX, 3, (255,0,0), 5)
                    #ISE NHI KARNA # cv2.imshow("Cropped", ik)
                    # # print("Right: ", h2x, h2y, h2w, h2h)
                    tx, ty, tw, th = 0, 0, 0, 0

                    if h1y < h2y:
                        ty = h1y
                        th = h2y + h2h - h1y
                    else:
                        ty = h2y
                        th = h1y + h1h - h2y

                    if h1x < h2x:
                        tx = h1x
                        tw = h2x + h2w - h1x
                    else:
                        tx = h2x
                        tw = h1x + h1w - h2x

                    tx -= 20
                    tw += 40
                    th += 20
                    ty -= 20

                    if tx < 0:
                        tx = 0
                    if tw > fw:
                        tw = fw
                    if ty < 0:
                        ty = 0
                    if th > fh:
                        th = fh
                    # print(ty, ty+th, tx, tx+tw)
                    # cv2.rectangle(img, (tx, ty), (tx+tw, ty+th), (0,0,0), 2)

                    imgWhite = np.ones((imgSize, imgSize, 3), np.uint8) * 255
                    imgCrop = img[ty:ty + th, tx:tx + tw]

                    imgCropShape = imgCrop.shape

                    aspectRatio = th / tw

                    if aspectRatio > 1:
                        k = imgSize / th
                        wCal = math.ceil(k * tw)
                        imgResize = cv2.resize(imgCrop, (wCal, imgSize))
                        imgResizeShape = imgResize.shape
                        wGap = math.ceil((imgSize - wCal) / 2)
                        imgWhite[:, wGap:wCal + wGap] = imgResize

                    else:
                        k = imgSize / tw
                        hCal = math.ceil(k * th)
                        imgResize = cv2.resize(imgCrop, (imgSize, hCal))
                        imgResizeShape = imgResize.shape
                        hGap = math.ceil((imgSize - hCal) / 2)
                        imgWhite[hGap:hCal + hGap, :] = imgResize

            # imgCrop= img[ty:ty+th , tx:tx+tw]
            # NAHI KARNA # cv2.imshow("Cropped", imgCrop)
            prediction, index = classifier.getPrediction(imgWhite)
            # print(prediction, index)

            # cv2.imshow("White", imgWhite)
        except:
            continue
    
    elif mode == 4:
        # print("Follow me mode on")
        ret, meriimg = read_frame()
        if not ret:
            errFile= open(VISION_EF_FILE, 'a')
            errFile.write("Vision warning: no image acquired during follow-mode frame read; retrying\n")
            errFile.close()
            time.sleep(0.2)
            continue

        #todo Add the code after testing
        
        meriimg= get_pose_detector().findPose(meriimg, draw= False)
        lmList, bboxInfo= get_pose_detector().findPosition(meriimg, draw= False)

        if bboxInfo:
            cenn= bboxInfo['center']
            leftShol= (lmList[11][1], lmList[11][2])
            rightShol= (lmList[12][1], lmList[12][2])
            # cv2.circle(img, rightShol, 10, (255,0,255), -1)
            # cv2.putText(img, "R", rightShol, cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 1)
            # cv2.putText(img, "L", leftShol, cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 1)
            centMid= [((leftShol[0]+rightShol[0])//2) , ((leftShol[1] + rightShol[1])//2)]
            # print(centMid)
            # cv2.circle(img, centMid, 10, (120,120,0), -1)
            # cv2.putText(img, "C", centMid, cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 1)
            
            # w, img, _ = psDetector.findDistance(leftShol, rightShol, img, True)
            w, _= get_face_mesh_detector().findDistance(rightShol, leftShol)
            W= 36.6
            
            # d= 30
            # f= (w*d)/W
            # print(f)
            f= 470

            d= int((W*f)/w)
            print(d)

            if 35 < d < 100:

                if centMid[0] < 250 or centMid[0] > 550:
                    yplace= int(round((6*centMid[0] + 3900)/70))
                    horMeAngle= abs(90-yplace)

                    timeForSide= round((horMeAngle/29), 2)
                    
                    if yplace < 90:
                        toRolls= f"l@{timeForSide}"
                        writeToRolls(toRolls)
                        print(toRolls)
                        time.sleep(timeForSide+3.5)
                        continue
                    else:
                        toRolls= f"r@{timeForSide}"
                        writeToRolls(toRolls)
                        print(toRolls)
                        time.sleep(timeForSide+3.5)
                        continue

                if d<45:
                    gujjuTime= 0.5
                elif d<50:
                    gujjuTime= 1.0
                elif d<55:
                    gujjuTime= 2
                else:
                    gujjuTime= (d-35)/10
                    gujjuTime= round(gujjuTime, 2)

                toRolls= f"f@{gujjuTime}"
                writeToRolls(toRolls)
                print(toRolls)
                time.sleep(gujjuTime+3.5)

            else:
                print("Stop")
                time.sleep(0.1)

_vision_stage("vision: shutdown")
visionWS.close()
visionEF= open(VISION_EF_FILE, 'a')
visionEF.write("2")
visionEF.close()
