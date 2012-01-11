import time
import re
import email.message
import sys
import email.mime
from email.mime.text import MIMEText

me = "Firstname Lastname <telnr@telephone.local>"

def contacts(fname):
    r  = {}
    f = open(fname)
    x = f.read()
    x = x.replace('\x00','')
    for contacttxt in re.findall("(?s)BEGIN:VCARD.*?END:VCARD",x):
        n = contacttxt.strip().split("\n")
        name=""
        tel = ""
        for line in n:
            if line.startswith("N:"):
                name = line.replace(";;","").strip()
                name = name.replace(";"," ")
                name=name[name.index(":")+1:]
            if line.startswith("FN:"):
                name = line.replace(";;","").strip()
                name = name.replace(";"," ")
                name = name[name.index(":")+1:]
            if line.startswith("TEL;"):
                tel = line.replace(";;","").strip()
                tel = tel.replace(";"," ")
                tel=tel[tel.index(":")+1:]
                tel = telnr(tel).as_inter()
                r[tel] = name
    return r
        
def smsread(fname,clist):
    f = open(fname)
    x = f.read()
    x = x.replace("\x00","") #lazy utf16? or ucs workaround
    f.close()
    smsen = []
    import datetime
    for smstext in re.findall("(?s)BEGIN:VMSG.*?END:VMSG",x):
        sms = dict()
        sms["data"] = smstext
        #subject:
        #from 0032@telephone.invalid
        #to 0032@telephone.invalid
        #phonebook lookup
        #add attachement
#        print smstext

        n = smstext.strip().split("\n")
        for (i,line) in enumerate(n):
            if line.startswith("N:"):
                name = line.replace(";;","").strip()
                name = name.replace(";"," ")
                name=name[name.index(":")+1:]
            if line.startswith("FN:"):
                name = line.replace(";;","").strip()
                name = name.replace(";"," ")
                name = name[name.index(":")+1:]
            if line.startswith("TEL:"):
                tel = line.replace(";;","").strip()
                tel = tel.replace(";"," ")
                tel=tel[tel.index(":")+1:]
                sms["tel"] = tel
            if line.startswith("X-IRMC-BOX"):
                sms["mbox"] = line.split(":")[1].strip()
            if line.startswith("Date:"):
                sms["date"] = line[len("Date:"):]
                sms["date"] = datetime.datetime.strptime(sms["date"],"%d.%m.%Y %H:%M:%S")
                sms["body"] = n[i+1]


        #print smstext
        #localtime issues?

        sms['Subject'] = "%s.."% sms["body"][:12] if len(sms["body"]) > 12 else sms["body"]
        nr = telnr(tel).as_inter()
        peer = "%s <%s@telephone.local>"% (clist[nr] if nr in clist else nr, nr)
        if sms["mbox"] == "SENT":
            sms['From'] = me
            sms['To'] = peer
        elif sms["mbox"] == "INBOX":
            sms['From'] = peer
            sms['To'] = me
        elif sms["mbox"] == "DRAFT":
            continue
        else:
            raise Exception(sms["mbox"])
        smsen.append(sms)
    return smsen

def calendar(fname):
    f = open(fname)
    x = f.read()
    f.close()
    s = ""
    s += "BEGIN:VCALENDAR\n"
    for text in re.findall("(?s)BEGIN:VEVENT.*?END:VEVENT",x):
        s += text
    s += "END:VCALENDAR\n"
    return s


class telnr:
    def __init__(self,s):
        self.nr = s
    def as_inter(self):
        s = self.nr
        if self.is_service():
            return s
        s = s.replace("/",'')
        s = s.replace(".",'')
        s = s.replace(" ",'')
        if not s.startswith("+"):
            if s.startswith("0"):
                s = s[1:]
            s = "0032"+s
        else:
            s = s.replace("+","00")
        return s

    def is_service(self):
        return len(self.nr)==4 or self.nr.startswith("#")
    def __cmp__(self,other):
        if isinstance(other,self.__class__):
            return self.as_inter() == other.as_inter()
        else:
            return self.as_inter() == telnr(other).as_inter()

    def __repr__(self):
        return self.nr

       
if __name__ == "__main__":

    clist= contacts(sys.argv[1])
    smsen = smsread(sys.argv[1],clist)
    import pprint
    #pprint.pprint(smsen)
    import email.message, email, mailbox
    from email.mime.text import MIMEText
    from email.Utils import formatdate
    from email.mime.multipart import MIMEMultipart
    m = mailbox.Maildir(sys.argv[2])
    for sms in smsen:
#        msg = email.message.Message()
        msg = MIMEMultipart()
        #m = email.message.Message()
        msg["From"] = sms["From"]
        msg["To"] = sms["To"]
        msg["Date"] = formatdate(float(sms["date"].strftime('%s')))
        msg["Subject"] = sms["Subject"]
        msg.attach(MIMEText(sms["body"]))
        msg.attach(MIMEText(sms["data"], _subtype='vcard'))
        m.add(mailbox.Message(msg))
    m.close()

    #cal= calendar(sys.argv[2])

    #for c in  clist.keys():
    #    print "%s => %s" % (c,standardize(c))
