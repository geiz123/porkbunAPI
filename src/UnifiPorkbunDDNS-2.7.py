#
# F'in debugger stop working!

#
# This is for python 2.7 and doesn't require extra modules
#

# urllib2 post: https://stackoverflow.com/a/4998300/3614460
import json
import urllib2

import traceback

import smtplib
from email.mime.text import MIMEText

from pprint import pprint

# https://stackoverflow.com/questions/42747469/how-to-pass-arguments-to-main-function-within-python-module
def doPorkbunDDNSUpdate(
    PorkbunSecretKey,
    PorkbunAPIKey,
    PorkbunDomain,
    PorkbunSubdomain,
    PorkbunType,
    PorkbunTTL,
    postmarkUser,
    postmarkPass,
    sender,
    recipients=None,
    awsSesUser=None,
    awsSesPass=None):
    """
    Update the domain IP when the WAN IP changes and send email alerts using Postmark or AWS SES as backup
    """
    if recipients not in (None, ''):
        recipients = recipients.split(',')
    else:
        recipients = {sender}

    # Porkbun Stuff
    PorkbunPingUrl = "https://api.porkbun.com/api/json/v3/ping"
    PorkbunRetrieveByNameTypeUrl = "https://api.porkbun.com/api/json/v3/dns/retrieveByNameType"
    PorkbunEditByNameTypeUrl = "https://api.porkbun.com/api/json/v3/dns/editByNameType"

    httpHeaders = {'Content-Type': 'application/json'}
    requestBody = {"secretapikey": PorkbunSecretKey, "apikey": PorkbunAPIKey}

    domainIP = ""
    wanIP = ""

    # GET CURRENT DOMAIN IP
    url = PorkbunRetrieveByNameTypeUrl + "/" + PorkbunDomain + "/" + PorkbunType + "/" + PorkbunSubdomain
    request = urllib2.Request(url, json.dumps(requestBody), httpHeaders)

    response = urllib2.urlopen(request)

    if response.code == 200:
        responseDict = json.load(response)
        # Get the domain IP
        domainIP = responseDict['records'][0]['content']

        # Get our WAN IP
        request = urllib2.Request(PorkbunPingUrl, json.dumps(requestBody),
                                httpHeaders)
        response = urllib2.urlopen(request)

        if response.code == 200:
            responseDict = json.load(response)
            wanIP = responseDict['yourIp']
            response.close()

            if wanIP not in (None, '') and wanIP != domainIP:
                # Update domain IP
                url = PorkbunEditByNameTypeUrl + "/" + PorkbunDomain + "/" + PorkbunType + "/" + PorkbunSubdomain

                # Add more stuff to request body. Currently porkbun only use what it so we could initialize the dict with everthing and reuse
                requestBody.update({"content": wanIP, "ttl": PorkbunTTL})

                # Do the POST
                request = urllib2.Request(url, json.dumps(requestBody),
                                        httpHeaders)
                response = urllib2.urlopen(request)

                if response.code == 200:
                    print("@@Update domain IP from " + domainIP + " to " + wanIP)

                    # Send email notification
                    try:
                        sendPostmarkSmtpToken("WAN IP Changed", domainIP + " -> " + wanIP, sender, recipients, postmarkUser, postmarkPass)
                        raise Exception('Test exeception')
                    except Exception as e:
                        print("@@Unable to send Postmark email, stack dump incoming...")
                        print(traceback.format_exc())

                        # Check if we should use backup
                        if awsSesUser is not None and awsSesPass is not None:
                            try:
                                print("Attempting to use AWS SES email backup...")
                                sendAwsSesSmtp("WAN IP Changed, BTW Postmark Failed", domainIP + " -> " + wanIP, sender, recipients, awsSesUser, awsSesPass)
                                print("Attempting to use AWS SES email backup...Success")
                            except Exception as e:
                                print("@@Unable to send AWS SES email, stack dump incoming...")
                                print(traceback.format_exc())
                else:
                    print(
                        "@@Unable to get WAN IP from porkbun ping, dumping response object..."
                    )
                    pprint(vars(response))
            else:
                print("@@WAN IP and Domain IP are still the same.")
        else:
            print(
                "@@Unable to get WAN IP from porkbun ping, dumping response object..."
            )
            pprint(vars(response))
    else:
        print("@@Unable to get IP from porkbun, dumping response object...")
        pprint(vars(response))

def sendGmail(subject, body, sender, recipients, password):
    """
    ** Deprecated **
    Send email using gmail smpt.

    You need to create an "App Password" from gmail to use -> https://myaccount.google.com/apppasswords
    It currently work but it might be disable later. Maybe use https://api.sendgrid.com/v3/mail/send

    Args:
        subject (str): Title
        body (str): Message
        sender (str): From
        recipients (list): To
        password (str): Password to gmail
    """
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtp_server.login(sender, password)
    smtp_server.sendmail(sender, recipients, msg.as_string())
    smtp_server.quit()
    print("Message sent!")

def sendPostmarkSmtpToken(subject, body, sender, recipients, accessKey, secretKey):
    """
    https://postmarkapp.com/developer/user-guide/send-email-with-smtp
    
    Send email using Postmark smpt token and TLS.

    Args:
        subject (str): Title
        body (str): Message
        sender (str): From
        recipients (list): To
        accessKey (str): access key
        secretKey (str): secret key
    """
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    smtp_server = smtplib.SMTP('smtp.postmarkapp.com', 25)
    smtp_server.starttls() # tell server we want to communicate with TLS encryption
    smtp_server.login(accessKey, secretKey)
    smtp_server.sendmail(sender, recipients, msg.as_string())
    smtp_server.quit()

def sendAwsSesSmtp(subject, body, sender, recipients, accessKey, secretKey):
    """
    Send email using AWS SES smpt token and TLS.

    Args:
        subject (str): Title
        body (str): Message
        sender (str): From
        recipients (list): To
        accessKey (str): access key
        secretKey (str): the SMPT password generated from the secret key
            see: https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html#smtp-credentials-convert
    """
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    smtp_server = smtplib.SMTP('email-smtp.us-east-2.amazonaws.com', 25)
    smtp_server.starttls() # tell server we want to communicate with TLS encryption
    smtp_server.login(accessKey, secretKey)
    smtp_server.sendmail(sender, recipients, msg.as_string())
    smtp_server.quit()

if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(
                    prog='UnifiPorkBunDDNS',
                    description='Intended to be run on Unifi OS with python 2.7 to update WAN IP with Porkbun domain IP when it changes and send email with Postmark SMTP if a change occur. AWS SES is an optional email backup. Provide the values if you want to activate it.',
                    epilog='github link here...')
    parser.add_argument('--porkbunSecretKey', required=True,
                        help='Porkbun secret key')
    parser.add_argument('--porkbunAPIKey', required=True,
                        help='Porkbun API key')
    parser.add_argument('--porkbunDomain', required=True,
                        help='Porkbun domain, ie: domain.io')
    parser.add_argument('--porkbunSubdomain', required=True,
                        help='Porkbun subdomain, ie: if full domain is dog.domain.io then subdomain is dog')
    parser.add_argument('--porkbunType', required=True,
                        help='Porkbun domain type, see your DNS management page for the info.')
    parser.add_argument('--porkbunTTL', required=True,
                        help='Porkbun TTL, see your DNS management page for the info.')
    parser.add_argument('--postmarkUser', required=True,
                        help='Postmark user')
    parser.add_argument('--postmarkPass', required=True,
                        help='Postmark password')
    parser.add_argument('--sender', required=True,
                        help='Address sending the email.')
    parser.add_argument('--recipients', required=False,
                        help='Address to receive the email. If not provided then --sender will be used. Seperate multiple recipients: dog@animal.com,cat@animal.com')
    parser.add_argument('--awsSesUser', required=False,
                        help='SES user')
    parser.add_argument('--awsSesPass', required=False,
                        help='SES password')
    args = parser.parse_args()
    doPorkbunDDNSUpdate(
        args.porkbunSecretKey,
        args.porkbunAPIKey,
        args.porkbunDomain,
        args.porkbunSubdomain,
        args.porkbunType,
        args.porkbunTTL,
        args.postmarkUser,
        args.postmarkPass,
        args.sender,
        args.recipients,
        args.awsSesUser,
        args.awsSesPass)