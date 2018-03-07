results = ""
# pip3 install dnspython termcolor requests
import os
import random
import requests
import urllib3
import dns.resolver #dnspython
import smtplib
import email
import getpass, poplib
import hashlib
import time
from termcolor import colored
import datetime
import sys

class Score(object):
    def __init__(self, service_name, status, error="No fail reason available."):
        self.name = service_name
        self.isUp = status
        self.error = error
        if status:
            self.status = "up"
        else:
            self.status = "down"

class Inject(object):
    def __init__(self, number, name, hours, minutes, filename):
        self.number = number
        self.name = name
        self.timedelta = datetime.timedelta(hours=int(hours), minutes=int(minutes))
        self.filename = 'injects/%s' % filename

def get_injects():
    injects_file = "wildcardinjects.txt"
    injects = []
    with open(injects_file, mode='r', encoding='utf8') as f:
        for line in f:
            (number, name, hours, minutes, filename) = line.split(",")
            injects.append(Inject(number, name, hours, minutes, filename))
    return injects

def random_ip():
    octet_1 = "10"
    octet_2 = str(random.randint(0,255))
    octet_3 = str(random.randint(0,255))
    octet_4 = str(random.randint(0,255))
    return "%s.%s.%s.%s" % (octet_1, octet_2, octet_3, octet_4)

def change_ip():
    do_not_use = ("10.0.0.0","10.255.255.254","10.255.255.255")
    ip = "10.0.0.0"
    scoring_interface = "ens192"

    while ip in do_not_use:
        ip = random_ip()
    
    os.system('ifdown %s' % (scoring_interface))
    os.system(r'sed -ri "s/IPADDR=10(\.[0-2]{0,1}[0-9]{1,2}){3}/IPADDR=%s/" /etc/sysconfig/network-scripts/ifcfg-%s' % (ip, scoring_interface))
    os.system('ifup %s' % (scoring_interface))

    print(ip)


def console_log_service(score):
    if score.isUp:
        status_msg = colored(' Up ', 'green')
    else:
        status_msg = colored('Down', 'red')
    print("Service: %-15s Status: [%s]" % (score.name, status_msg))

def start_scoring(injects):
    while(True):
        sleep_time = 0
        start_time = time.time()
        test_services(injects)
        end_time=time.time()
        
        execution_time = end_time - start_time
        if execution_time >= 60:
            sleep_time = 0
        else:
            sleep_time = 60 - execution_time

        time.sleep(sleep_time)

def test_services(injects):
    change_ip()
    tests = [
        http_test(),
        https_test(),
        ubuntu_test(),
        addns_test(),
        webmail_test(),
        pop3_test(),
        smtp_test()
    ]
    print(chr(27) + "[2J")
    for test in tests:
        console_log_service(test)
    update_html(tests, injects)

def update_html(tests, injects):

    html_location = "/var/www/html/index.html"

    with open('webtemplate/top.template', 'r', encoding='utf8') as myfile:
        top=myfile.read()
    with open('webtemplate/bottom.template', 'r', encoding='utf8') as myfile:
        bottom=myfile.read()

    generic_line = '        <tr><td class="label">%s</td><td class="%s">%s</td></tr>\n'
    generic_inject = '    <p><b>Inject %s: </b><a href="%s" target="_blank">%s</a> - %s</p>'
    dynamic_lines = "<h2>%s</h2>" % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for test in tests:
        dynamic_lines += generic_line % (test.name, test.status, test.status.capitalize())
    
    dynamic_lines+="    </table>"
    dynamic_lines+="    <h2>Injects</h2>"
    
    for inject in injects:
        inject_time = start_time + inject.timedelta

        if datetime.datetime.now() > inject_time:
            inject_time_string = inject_time.strftime('%H:%M:%S')
            dynamic_lines += generic_inject % (inject.number, inject.filename, inject.name, inject_time_string)

    html = top + dynamic_lines + bottom
    

    with open(html_location, 'w') as html_file:
        #text_file.write(snippet)
        html_file.write(html)


def get_credentials(credentials_file):
    credentials = {}
    with open(credentials_file, mode='r', encoding='utf8') as f:
        for line in f:
            (username, password) = line.split(":")
            credentials[username] = password.replace('\n', '')
    return credentials

def filter_nonprintable(text):
    import string
    # Get the difference of all ASCII characters from the set of printable characters
    nonprintable = set([chr(i) for i in range(128)]).difference(string.printable)
    # Use translate to remove all non-printable characters
    return text.translate({ord(character):None for character in nonprintable})

def pop3_test():
    test_name = 'POP3'
    test_credentials = get_credentials('accounts.txt')
    test_server = "172.25.%s.39" % third_octet
    test_port = "110"

    username, password = random.choice(list(test_credentials.items()))
    dir_list = os.listdir("emails/" + username)
    number_files = len(dir_list)
    test_mail_number = random.randint(1,number_files)
    test_mail_file = "emails/" + username + "/" + str(test_mail_number)
   
    with open(test_mail_file, 'r', encoding='utf8') as reffile:
        test_mail_reference_hash = reffile.read().replace('\n', '')


    try:
        # Change to poplib.POP3_SSL()
        Mailbox = poplib.POP3(test_server, test_port) 
        Mailbox.user(username) 
        Mailbox.pass_(password)
        test_mail = b"\n".join(Mailbox.retr(test_mail_number)[1])
        test_parsed_mail = email.message_from_bytes(test_mail)
        snippet = str(test_parsed_mail['From']) + str(test_parsed_mail['To']) + str(test_parsed_mail['Date']) + str(test_parsed_mail['Subject'])
        test_mail_live_hash = hashlib.md5(str(snippet).encode('utf-8')).hexdigest()

        # Check against reference hash
        if test_mail_live_hash == test_mail_reference_hash:
            return Score(test_name, True)
        else:
            return Score(test_name, False)
        #for msg in Mailbox.retr(test_email_number)[1]:
        #        print(msg)
    except Exception as e:
        #print(e)
        print("Error fail" + str(e))
        return Score(test_name, False)


def smtp_test():
    test_name = "SMTP"
    test_server = "172.25.%s.39" % third_octet
    # Import smtplib for the actual sending function
   
    #Clean this code up lmao, lazy tho
    test_credentials = get_credentials('accounts.txt')
    username, password = random.choice(list(test_credentials.items()))
    fromAddress = '%s@team.local' % username
    username, password = random.choice(list(test_credentials.items()))
    toAddress = '%s@team.local' % username

    message = email.message_from_string('''To: <%s>
    From: <%s>
    Reply-To: <%s>
    Subject: Test send mail \n\n Hello''' % (toAddress, toAddress, fromAddress)) 

    try:
        smtp = smtplib.SMTP()
        smtp.connect(test_server)
    except Exception as e:
        return Score(test_name, False)
    #try:
    #    smtp.login('rwilson','tree22')
    #except Exception:
    #    print('Login Failed!')
    try:
        smtp.sendmail(fromAddress,toAddress ,message.as_string())
        smtp.close()
        return Score(test_name, True)
    except Exception as e:
        return Score(test_name, False)

def webmail_test():
    test_name = "Mail - HTTP"
    test_server = "172.25.%s.39" % third_octet
    test_type = "http" 
    score = Score(test_name, True)
    test_uris = (
                    '/index.php',
                    '/phpchat/index.php',
                    '/squirrelmail/index.php'
                )
    test_strings = [
                    ('Welcome to Team Webmail','Password','Username</label>'),
                    ('"themes/default/smileys/msn_cigarette.gif"','<p>See the quick demo :</p>','My chat'),
                    ('<b>SquirrelMail Login</b>','name="login_username" value=""','<input type="password"')
                ]
    headers = {
        'User-Agent': ''
    }
    ## Choose random uri to test
    uri_index = random.randint(0,2)

    # Format URL
    test_url = "%s://%s%s" % (test_type, test_server, test_uris[uri_index])
 
    try:
        test_response  = requests.get(test_url, headers=headers)
        for test_string in test_strings[uri_index]:
            if test_string in str(test_response.content):
                pass
            else:
                score = Score(test_name, False)
                break

        return score
    except Exception as e:
        print(e)
        return Score(test_name, False)

def http_test():
    test_name = "Ecom - HTTP"
    test_server = "172.25.%s.11" % third_octet
    test_type = "http" 
    score = Score(test_name, True)
    test_uris = (
                    '/index.php',
                    '/index.php?page=shop.browse&category_id=1&option=com_virtuemart&Itemid=1&vmcchk=1&Itemid=1',
                    '/index.php?page=shop.browse&category_id=3&option=com_virtuemart&Itemid=1&vmcchk=1&Itemid=1',
                    ':8080/ehour/eh/login/Login'
                )
    test_strings = [
                    ('We have the best widgets for do-it-yourselfers.  Check us out!','Posters','Stickers', 'Your Cart is currently empty.'),
                    ('$42.22','$34.64','$53.04', 'Look-alike Gnome', 'Gnome Standing Tall', 'Bushel Gnome'),
                    ('$20.57','$12.99', '$9.74', 'Deluxe Gnome Pictures', 'Gnome History', 'How To Survive A Garden Gnome Attack', 'Deluxe photos of famous gnomes', 'A book related', 'Good information to have and keep'),
                    ('username:</td>','password"</td>','Sign in &gt;&gt;"/></td>')
                ]
    headers = {
        'User-Agent': ''
    }
    ## Choose random uri to test
    uri_index = random.randint(0,2)

    # Format URL
    test_url = "%s://%s%s" % (test_type, test_server, test_uris[uri_index])
    try:
        test_response  = requests.get(test_url, headers=headers)
        for test_string in test_strings[uri_index]:
            if test_string in str(test_response.content):
                pass
            else:
                score = Score(test_name, False)
                print(test_string)
                break

        return score
    except Exception as e:
        print(e)
        return Score(test_name, False)

def https_test():
    test_name = "Ecom - HTTPS"
    test_server = "172.25.%s.11" % third_octet
    test_type = "https" 
    score = Score(test_name, True)
    test_uris = (
                    '/index.php',
                    '/index.php?page=shop.browse&category_id=1&option=com_virtuemart&Itemid=1&vmcchk=1&Itemid=1',
                    '/index.php?page=shop.browse&category_id=3&option=com_virtuemart&Itemid=1&vmcchk=1&Itemid=1'
                )
    test_strings = [
                    ('We have the best widgets for do-it-yourselfers.  Check us out!','Posters','Stickers', 'Your Cart is currently empty.'),
                    ('$42.22','$34.64','$53.04', 'Look-alike Gnome', 'Gnome Standing Tall', 'Bushel Gnome'),
                    ('$20.57','$12.99', '$9.74', 'Deluxe Gnome Pictures', 'Gnome History', 'How To Survive A Garden Gnome Attack', 'Deluxe photos of famous gnomes', 'A book related', 'Good information to have and keep')
                ]
    headers = {
        'User-Agent': ''
    }
    ## Choose random uri to test
    uri_index = random.randint(0,2)

    # Format URL
    test_url = "%s://%s%s" % (test_type, test_server, test_uris[uri_index])
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        test_response  = requests.get(test_url, headers=headers, verify=False)
        for test_string in test_strings[uri_index]: 
            if test_string in str(test_response.content):
                pass
            else:
                score = Score(test_name, False)
                print(test_string)
                break

        return score
    except Exception as e:
        print(e)
        return Score(test_name, False)

def ubuntu_test():
    test_ips = ('172.25.%s.39' % third_octet,
                '172.25.%s.23' % third_octet,
                '172.25.%s.11' % third_octet)
    test_records = ('mail.team.local',
                    'dns.team.local',
                    'www.team.local')
    test_server = "172.25.%s.23" % third_octet
    test_name = "DNS"

    ## Choose random record to text
    record_index = random.randint(0,2)

    ###
    test_response = ""

    ubuntu_tester = dns.resolver.Resolver() #create a new instance named 'ubuntu_tester'
    ubuntu_tester.nameservers = [test_server]

    try:
            response_ubuntu = ubuntu_tester.query(test_records[record_index], "A")

            test_response = response_ubuntu[0].to_text()

            if test_response == test_ips[record_index]:
                return Score(test_name, True)
            else:
                #print("Actual: %s Reference: %s" % (test_response, test_ips))
                return Score(test_name, False)
                  
    except Exception as e:
        #print("Exception")
        return Score(test_name, False)

def addns_test():
    test_ips = ('172.25.%s.39' % third_octet,
                '172.25.%s.23' % third_octet,
                '172.25.%s.11' % third_octet)
    test_records = ('mail.team.local',
                    'dns.team.local',
                    'www.team.local')
    test_server = "172.25.%s.27" % third_octet
    test_name = "ADDNS"

    ## Choose random record to text
    record_index = random.randint(0,2)

    ###
    test_response = ""

    ubuntu_tester = dns.resolver.Resolver() #create a new instance named 'ubuntu_tester'
    ubuntu_tester.nameservers = [test_server]

    try:
            response_ubuntu = ubuntu_tester.query(test_records[record_index], "A")
            test_response = response_ubuntu[0].to_text()

            if test_response == test_ips[record_index]:
                return Score(test_name, True)
            else:
                #print("Actual: %s Reference: %s" % (test_response, test_ips))
                return Score(test_name, False)
                  
    except Exception as e:
        #print(e
        #print("Actual: %s Reference: %s" % (test_response, test_ips))
        return Score(test_name, False)


if len(sys.argv) == 2:
    if sys.argv[1] == "new":
        start_time = datetime.datetime.now()
    elif sys.argv[1] == "old":
        pass

    if int(sys.argv[2]) > 0 and int(sys.argv[2]) < 30:
        team_number = int(sys.argv[2])
        base_third_octet = 20
        third_octet = base_third_octet + team_number

    injects = get_injects()
    start_scoring(injects)
else:
    print("script should be run like: \"scoringengine.py new|old $teamnumber\"")
    print("ex) scoringengine.py old 3")