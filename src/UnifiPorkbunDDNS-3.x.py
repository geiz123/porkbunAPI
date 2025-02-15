#
# For python 3.x no 3rd party modules. Update setup.ps1 before testing in vscode
# For 3rd party stuff see: https://github.com/porkbundomains/porkbun-dynamic-dns-python
#

import datetime
import json
import traceback
import smtplib
import urllib.parse
import urllib.request
import urllib.response
from email.mime.text import MIMEText
from pprint import pprint, pformat

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

    requestBody = {"secretapikey": PorkbunSecretKey, "apikey": PorkbunAPIKey}

    domainIP = getPorkbunDomainIp(PorkbunDomain, PorkbunSubdomain, PorkbunType, requestBody)
    wanIP = getWanIp(requestBody)

    if wanIP != domainIP:
        updatePorkbunDomainIp(PorkbunDomain, PorkbunSubdomain, PorkbunType, PorkbunTTL, requestBody, wanIP)

        # Send email notification
        try:
            sendPostmarkSmtpToken("WAN IP Changed", domainIP + " -> " + wanIP, sender, recipients, postmarkUser, postmarkPass)
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
        print(f"[{str(datetime.datetime.now()).split('.')[0]}] @@WAN IP and Domain IP are still the same.")

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

def updatePorkbunDomainIp(PorkbunDomain, PorkbunSubdomain, PorkbunType, PorkbunTTL, requestBody, newIp):
    """
    Update domain's IP on porkbun

    Args:
        PorkbunDomain (str): Porkbun domain, ie: domain.io
        PorkbunSubdomain (str): Porkbun subdomain, ie: if full domain is dog.domain.io then subdomain is dog
        PorkbunType (str): Porkbun domain type, see your DNS management page for the info.
        requestBody (dict): Dict with the API key and secret key {"secretapikey": secretKey, "apikey": apiKey}
        newIp (str): IP to replace the domain's IP on porkbun
    Raises:
        Exception when fail to open connection to porkbun ping API or response is not 200.
    """
    PorkbunEditByNameTypeUrl = "https://api.porkbun.com/api/json/v3/dns/editByNameType"
    url = PorkbunEditByNameTypeUrl + "/" + PorkbunDomain + "/" + PorkbunType + "/" + PorkbunSubdomain

    # Add more stuff to request body. Currently porkbun only use what it so we could initialize the dict with everthing and reuse
    requestBody.update({"content": newIp, "ttl": PorkbunTTL})

    request = urllib.request.Request(url, json.dumps(requestBody).encode('utf-8'))
    
    try:
        response = urllib.request.urlopen(request)
    except Exception as e:
        raise Exception(f'Fail to open connection to {url}.') from e
    else:
        with response:
            if response.code != 200:
                raise Exception(f"@@Fail to update domain's IP using:\nURL:{url}\nPorkbunTTL:{PorkbunTTL}\nDumping response object...\n{pformat(vars(response))}")

def getPorkbunDomainIp(PorkbunDomain, PorkbunSubdomain, PorkbunType, requestBody):
    """
    Get the IP of a specific domain on Porkbun

    Args:
        PorkbunDomain (str): Porkbun domain, ie: domain.io
        PorkbunSubdomain (str): Porkbun subdomain, ie: if full domain is dog.domain.io then subdomain is dog
        PorkbunType (str): Porkbun domain type, see your DNS management page for the info.
        requestBody (dict): Dict with the API key and secret key {"secretapikey": secretKey, "apikey": apiKey}
    Returns:
        The domain's IP on Porkbun
    Raises:
        Exception when fail to open connection to porkbun ping API or response is not 200.
    """
    PorkbunRetrieveByNameTypeUrl = "https://api.porkbun.com/api/json/v3/dns/retrieveByNameType"
    url = PorkbunRetrieveByNameTypeUrl + "/" + PorkbunDomain + "/" + PorkbunType + "/" + PorkbunSubdomain

    request = urllib.request.Request(url, json.dumps(requestBody).encode('utf-8'))
    
    try:
        response = urllib.request.urlopen(request)
    except Exception as e:
        raise Exception(f'Fail to open connection to {url}.') from e
    else:
        with response:
            if response.code == 200:
                responseDict = json.load(response)
                return  responseDict['records'][0]['content']
            else:
                raise Exception(f"@@Unable to get domain's IP from porkbun, dumping response object...\n{pformat(vars(response))}")

def getWanIp(requestBody):
    """
    Use porkbun API ping to get our WAN IP.

    Args:
        requestBody: Dict with the API key and secret key {"secretapikey": secretKey, "apikey": apiKey}
    Returns:
        Your WAN IP
    Raises:
        Exception when fail to open connection to porkbun ping API or response is not 200.
    """
    PorkbunPingUrl = "https://api.porkbun.com/api/json/v3/ping"
    request = urllib.request.Request(PorkbunPingUrl, json.dumps(requestBody).encode('utf-8'))
    
    try:
        response = urllib.request.urlopen(request)
    except Exception as e:
        raise Exception(f'Fail to open connection to {PorkbunPingUrl}.') from e
    else:
        with response:
            if response.code == 200:
                responseDict = json.load(response)
                return responseDict['yourIp']
            else:
                raise Exception(f"@@Unable to get WAN IP from porkbun ping, dumping response object...\n{pformat(vars(response))}")

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
    raise Exception("Test fail postmark")
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
                    description='This program will update Porkbun domain IP with our WAN IP if they are different. Send email with Postmark SMTP if a change occur. AWS SES is an optional email backup. Provide the values (awsSesUser and awsSesPass) if you want to activate it.',
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