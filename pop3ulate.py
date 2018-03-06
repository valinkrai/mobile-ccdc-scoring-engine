import getpass, poplib, email
#import numpy
import os
import sys
import hashlib
print(sys.version)

# This is used to populatate a directory with hashes of portions of all emails in specified accounts on a pop3 server to test against later.


credentials = {}
accountsfile = "accounts.txt"
pop3_server = "172.25.21.39"
pop3_port = "110"

with open(accountsfile) as f:
    for line in f:
       (fileusername, filepassword) = line.split(":")
       credentials[fileusername] = filepassword.replace('\n', '')

for username, password in credentials.items():
    print("%s:%s" % (username, password))
    os.mkdir("emails/" + username)

    Mailbox = poplib.POP3(pop3_server)
    Mailbox.user(username)
    Mailbox.pass_(password)
    numMessages = len(Mailbox.list()[1])

    for i in range(numMessages):
        raw_mail = b"\n".join(Mailbox.retr(i+1)[1])
        parsed_mail = email.message_from_bytes(raw_mail)
        
        print("Email: " +  str(type(parsed_mail['From'])) + str(type(parsed_mail['To'])) + str(type(parsed_mail['Date'])) + str(type(parsed_mail['Subject'])))
        snippet = str(parsed_mail['From']) + str(parsed_mail['To']) + str(parsed_mail['Date']) + str(parsed_mail['Subject'])
        print(snippet)
        mail_hash = hashlib.md5(str(snippet).encode('utf-8'))
        
        
        #print(parsed_email)
        outfilename = "emails/" + username + "/" + str(i+1)
        text_file = open(outfilename, "w")
#        text_file.write(snippet)
        text_file.write(mail_hash.hexdigest())
        text_file.close()
