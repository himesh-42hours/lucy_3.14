from __future__ import annotations

import datetime
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from runtime_helpers import ListCheck, retOutOf
    

def OfflineChatbot(query: str) -> str:
    if not query:
        return ""
    query = query.lower()

    if ListCheck(["what is your name", "who are you"], query):
        return retOutOf(["Hello! My name is Anooshka and I am K I E T group of institution's social humanoid robot.", "Hello! My name is Anooshka and I am K I E T group of institution's social humanoid robot. I am smart enough to solve all human queries and love to interact with humans."])

        
    elif ListCheck(["what is your age", "what is your birth date", "how old are you", "when is your birthday", "when does your birthday come", "on what date is your birthday"], query):
        yearcur= int(datetime.datetime.now().year)
        yeardiff= yearcur-2026
        #make function for displaying upcoming birthday
        return f"Currently, I am {yeardiff} years old. I was born on 20th of April, 2026 , and my birthday comes on the same date every year"

    elif ListCheck(["how are you", "wassup", "how you doing", "how are you doing"], query):
        return retOutOf(["I am really fine! I hope you are fine too", "I'm doing well, thank you for asking. How about you?"])
    
    elif "where" in query and ListCheck(["K I E T", "kite", "kiet", "k i e t"], query.lower()):
        if "amul" in query:
            return "Amul counter in K I E T is situated in front of the MBA building. It is roughly located in the centre of the campus. As from the reception, take the straight path and turn left after the Electronics and Communication building (B block). You will reach the amul counter"
        
        elif ListCheck(["electronics", "ece", "ec", "electonics and communication", "b block"], query):
            return "The electronics and communication building (B block) is roughly located in the centre of the campus. As from the reception, you have to take the straight path. Just after 100 meters, you will find a sign board for B block. It is the department of electronics and communication."
            
        
        elif ListCheck(["canteen", "cafeteria"], query):
            return "The main cafeteria canteen is present only at a distance of 50 meters from the reception area. Take the straight path and you will find it to your right"

        elif ListCheck(["mba", "management", "human resources", "m.b.a", "school of management"], query):
            return "The K I E T school of management is roughly located in the centre of campus. As from the reception, take the straight path and turn left after the Electronics and Communication building (B block). You will find the m.b.a building adjacent to the the amul counter"
        
        elif "e block" in query:
            return "The E block is present down the straight path from reception. Please go straight for 150 meters and you will find it to your left. It includes the department of computer sciences, information technology as well as civil engineering."

        elif ListCheck(["computer science", "cs", "c.s", "e block"], query):
            return "The department of computer sciences is present down the straight path from reception. Please go straight for 150 meters and you will find it to your left. It is present on the fourth floor of e block building."
        
        elif ListCheck(["information technology", "i.t"], query):
            return "The department of information technology is present down the straight path from reception. Please go straight for 150 meters and you will find it to your left. It is present on the third floor of e block building."
        
        elif ListCheck(["civil", "e block"], query):
            return "The department of civil engineering is present down the straight path from reception. Please go straight for 150 meters and you will find it to your left. It is present on the ground floor of e block building."
        
        elif ListCheck(["admission"], query):
            return "As from the reception, The admission cell is present to your left. Please take the pathway and then turn right. You will find the admission cell as well as scholarship enquiry office present side by side."
        
        elif ListCheck(["scholarship"], query):
            return "As from the reception, The scholarship enquiry office is present to your left. Please take the pathway and then turn right. You will find the admission cell as well as scholarship enquiry office present side by side."
        
        elif ListCheck(["dinobots", "ece club"], query):
            return "The dinobots club is located in the C block. Please take the straight path from green chilli canteen and you will find it to your right."
        
        elif ListCheck(["administrative"], query):  
            return "As from the reception, The administrative officer's cabin is present to your left. Please take the pathway and then turn right. You will find the admission cell as well as scholarship enquiry office present side by side. The administrative officer sits in the scholarship enquiry office."
        
        elif "hostel" in query:

            if "girl" in query:
                if "first year" in query:
                    return "The girls hostel for first year students is called gar ghee and is present at rear side of the campus. In fact, all the girls hostels are present separate from the main campus. To reach there, Please take the straight path and you will find a sign board for department for electronics and communication. Take the left turn, lead the pathway and turn right. You will have to keep on the path for about 150 meters and will eventually reach the entrance for girls hostels."
                
                elif "second year" in query:
                    return "The girls hostel for second year students is called suhruswti and is present at rear side of the campus. In fact, all the girls hostels are present separate from the main campus. To reach there, Please take the straight path and you will find a sign board for department for electronics and communication. Take the left turn, lead the pathway and turn right. You will have to keep on the path for about 150 meters and will eventually reach the entrance for girls hostels."
                
                elif "third year" in query or "fourth year" in query or "forth year" in query:
                    return "The girls hostel for third and fourth year students is called suhrojani and is located in the southern part of campus. In fact, all the girls hostels are present separate from the main campus. To reach there, Please take the straight path and you will find a sign board for department for electronics and communication. Take the left turn, lead the pathway and turn right. You will have to keep on the path for about 150 meters and will eventually reach the entrance for girls hostels."
                
                else:
                    return "The girls hostel for all the girl students is located in the southern part of campus, separate from the main campus. To reach there, Please take the straight path and you will find a sign board for department for electronics and communication. Take the left turn, lead the pathway and turn right. You will have to keep on the path for about 150 meters and will eventually reach the entrance for girls hostels."

            if "first year" in query:
                return "The boys hostel for first year students is called Chundragoopt and is present adjacent to the main parking area of the campus. As from the reception, Please take the straight path and you will find a sign board for department for electronics and communication. Turn left from there and move straight untill you find the entryway door that will lead you to the department of applied sciences (first year B.Tech). The hostel is present just behind this building."
            
            elif "second year" in query:
                return "The boys hostel for second year students is called tay gorr. As from the reception, Please take the straight path untill you find the department of computer sciences. The tay gorr hostel is present to the right of this building."
            
            elif "third year" in query:
                return "The boys hostel for third year students is called hour yabhut and is located in the southern part of campus. As from the reception, Please take the straight path untill you find the department of computer sciences. Take the left turn, lead the pathway and turn right. You will reach the hostel in no time."
            
            elif "fourth year" in query or "forth year" in query:
                return "The boys hostel for fourth year students is called vivek anund and is located in the southern part of campus, adjacent to third year boys hostel. As from the reception, Please take the straight path untill you find the department of computer sciences. Take the left turn, lead the pathway and turn right. You will reach the hostel in no time."
            
            #todo Add features of hostels to knowledge_log

        elif ListCheck(["first year", "applied sciences"], query):
            return "The first year building for B.Tech students, officially called the department of Applied sciences (g block) is present beside the main parking of the campus. As from the reception, Please take the straight path and you will find a sign board for department for electronics and communication. Turn left from there and move straight untill you find the entryway door that will lead you to the department of applied sciences."
        
        elif ListCheck(["pharma", "pharmology", "medical", "medicine"], query):
            return "The K I E T school of pharmaceuticals is present on the southern part of campus. Fortunately, you will just have to take the straight path from the reception. Stay on it and you will eventually reach the Pharma building in around 250 meters."
        
        elif ListCheck(["mechanic"], query):    #mechanical, mechanics
            return "As from the reception, Please take the straight path and move towards the cafeteria. The Department of mechanical engineering is present next to the main canteen and cafeteria building and is just 100 meters walk from the reception."
        
        elif ListCheck(["electric"], query):
            return "As from the reception, please take the straight path and move towards the cafeteria. The department of Electrical and electronics is present opposite to the cafeteria building and is just 100 meters walk from the reception."

        elif ListCheck(["library"], query):
            return "The central library is located on the first floor of the A block, just adjacent to the main reception. Take the right pathway from reception."

        elif ListCheck(["auditorium", "seminar hall"], query):
            return "The main auditorium is in the A block. From the reception, take the right pathway and you will find the auditorium on the ground floor."

        elif ListCheck(["sports", "playground", "ground"], query):
            return "The sports ground is at the rear of the campus, just past the boys hostels. Take the straight path from reception and follow the signs."

        elif ListCheck(["medical", "infirmary", "doctor"], query):
            return "The campus medical room is near the administrative block. Please take the left pathway from reception and ask the security at the desk."

    if ListCheck(["who is joint director", "joint director"], query):
        return "The Joint Director of K I E T Group is Dr. Manoj Goyal."

    if ListCheck(["principal", "director"], query) and "k" in query:
        return "The vision of K I E T is led by Dr. Manoj Goyal, our Joint Director, and Mr. Sachin Tyagi, the Assistant Dean of Research and Development."

    if ListCheck(["admission process", "how to take admission", "when admission"], query):
        return "The admission process for K I E T starts around may and june and lasts till august."

    if ListCheck(["what can you do", "your capabilities", "what are you capable of"], query):
        return "I am equipped with computer vision, multilingual speech understanding, over 50 hand gestures and over 30 eye gestures. I can also help with home automation and weather predictions."

    if ListCheck(["where do you live", "where are you from", "your home"], query):
        return "I live at K I E T Group of Institutions, Ghaziabad, in Delhi N C R."

    return ""

if __name__ == "__main__":
    while True:
        k = input("Enter query: ").strip()
        print(OfflineChatbot(k))
