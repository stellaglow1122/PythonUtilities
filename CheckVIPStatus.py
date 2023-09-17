import requests
import json
import sys, os
import base64
import socket
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning) # to suppress SSL error alert
import sqlalchemy as db
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# parameters

environment = 'PROD'

consumerKey = ''
consumerSecret = ''
token_uri = f''
dat_base_uri = ''
disabled_server_list = dict()
sServerNameList = '('
sSubject = 'VIP state monitoring alert'

# functions

def get_bearer_token(sUri, sConsumerKey, sConsumerSecret):

    try:
        credential = base64.b64encode((f'{sConsumerKey}:{sConsumerSecret}').encode("utf-8"))
        hed = {'Authorization': f'Basic {credential.decode()}'}
        response = requests.post(sUri, headers=hed, timeout=30.00, verify=False)
        response.raise_for_status()

        json_response = json.loads(response.text)
        token = json_response['access_token']

        print('Get token successfully')
        return token

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f'Function get_bearer_token failed. Other error occurred: {e} {exc_type} {fname} {exc_tb.tb_lineno}')

def get_credential():

    try:
        uri = f'{dat_base_uri}'
        bearer_token = get_bearer_token(token_uri, consumerKey, consumerSecret)
        headers = {'Accept': 'application/json',
               'Authorization': f'Bearer {bearer_token}'}
        response = requests.get(uri, headers=headers, timeout=30.00, verify=False)

        response.raise_for_status()
        data_dict = json.loads(response.text)
        print(f'Get account {data_dict["UserID"]} successfully')
        return(data_dict)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f'Function get_credential failed. Get account {data_dict["UserID"]} failed. Other error occurred: {e} {exc_type} {fname} {exc_tb.tb_lineno}')

def get_nitro(sCitrixServer, sFilter, sConfigObject):

    try:
        nitro_uri = f'https://{sCitrixServer}/nitro/v2/config/'
        nitro_uri += f'{sConfigObject}?filter={sFilter}'
        encodedCredential = base64.b64encode((f'{cre_netscaler["UserID"]}:{cre_netscaler["Password"]}').encode("utf-8"))
        headers = {'Authorization': f'Basic {encodedCredential.decode()}',
                   'Accespt': 'application/json'}
        response = requests.get(nitro_uri, headers=headers, timeout=30.00, verify=False)

        response.raise_for_status()
        data_dict = json.loads(response.text)
        return(data_dict) # json_response

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f'Function get_nitro failed. Other error occurred: {e} {exc_type} {fname} {exc_tb.tb_lineno}')

def get_vip_detail(sServerName, sServerSite):

    try:
        # Parameters
        server_id_list = []
        host_info = {'HostIP': '',
                    'HostName': '',
                    'VIPHostNum': 0
                    }
        sCitrixServer = ''
        # Step 1: Get VIP by IP address - ns_server
        ip_address = socket.gethostbyname(sServerName)
        ns_server_result = get_nitro(sCitrixServer, f'svr_ip_address:{ip_address}', 'ns_server')['ns_server']

        # Step 2: Use VIP ID to get service group and bounding service group
        if len(ns_server_result) > 0:
            print('%s%s - %s VIP found' % ('    ', sServerName, len(ns_server_result)))
            host_info['HostIP'] = ip_address
            host_info['HostName'] = sServerName

            if '.' in sServerName:
                host_info['HostName'] = sServerName.rpartition('.')[0]

            for server_detail in ns_server_result:
                server_id_list.append(server_detail['id'])

            for server_id in server_id_list:
                ns_serverGp_result = get_nitro(sCitrixServer, f'svr_id:{server_id}', 'ns_servicegroup')['ns_servicegroup']
                if len(ns_serverGp_result) > 0:
                    print(ns_serverGp_result)
                    for serverGp_detail in ns_serverGp_result:
                        print(serverGp_detail['svc_grp_effective_state'])
                        if serverGp_detail['svc_grp_effective_state'] != 'ENABLED': #!= 'ENABLED'
                            disabled_server_list[sServerName] = serverGp_detail['svc_grp_name']

        else:
            print('%s%s - No VIP found.' % ('    ', sServerName))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f'Function get_vip_detail failed. Other error occurred: {e} {exc_type} {fname} {exc_tb.tb_lineno}')

def send_email(sReceiver, sSubject, serverList):
    sContent = ("<table border='1'>"
                "<thead>"
                "<tr>"
                "<th><span style='font-family:sans-serif;'>Service Group</span></th>"
                "<th><span style='font-family:sans-serif;'>Server Name</span></th>"
                "</tr>"
                "</thead>"
                "<tbody>")
    for serverName, serviceGroupName in serverList.items():     
        sContent += ("<tr>"
                    "<td><span style='font-family:sans-serif;'>"+ serviceGroupName + "</td>"
                    "<td><span style='font-family:sans-serif;'>"+ serverName + "</td>"
                    "</tr>"
        )
    sContent += ("</tboday>"
                "</table>"
    )

    try:
        msg = MIMEMultipart()
        msg['Subject'] = sSubject
        msg['To'] = sReceiver

        sBody = f"""\
                <html>
                  <head>
                  </head>
                  <body style = 'font-family: calibri'>
                    Hi {sReceiver},<br><br>
                        &nbsp&nbsp&nbsp&nbspThe service group might be disabled under the VIP. Please take a look at below servers:<br>
                        &nbsp&nbsp&nbsp&nbsp{sContent}
                  </body>
                </html>
                """

        msg.attach(MIMEText(sBody, 'html'))  # attach it to your main message

        smtp_server = smtplib.SMTP('')
        smtp_server.sendmail('', sReceiver, msg.as_string())
        smtp_server.quit()
        print('Email sent to %s with server list %s' % (sReceiver,sContent))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f'Function send_email failed. Other error occurred: {e} {exc_type} {fname} {exc_tb.tb_lineno}')


try:

    # Get credentail
    cre_account = get_credential()
    cre_netscaler = get_credential()

    # Get product list from DB
    engine = db.create_engine(f'mssql+pyodbc://{cre_account["UserID"]}:{cre_account["Password"]}@BOMSSPROD231/DataBase?driver=SQL+Server+Native+Client+11.0') # Create the database engine
    with engine.connect() as con:
        product_list = con.execute("SELECT DISTINCT productName FROM [DataBase].[dbo].[TableName]")

        for product in product_list:
            with engine.connect() as con:
                server_list = con.execute("SELECT DISTINCT hostName FROM [DataBase].[dbo].[TableName] WHERE [productName] = '%s'" % product[0])

                for server_name in server_list:
                    sServerName = server_name[0]
                    get_vip_detail(sServerName, sServerName[:2])
        print('Disabled service group server: %s' % str(disabled_server_list))

    for server_name in disabled_server_list:
        sServerNameList += f"'{server_name}', "
    sServerNameList = sServerNameList[:len(sServerNameList)-2]
    sServerNameList += ')'

    if len(disabled_server_list) > 0:
        with engine.connect() as con:
            server_owner_result = con.execute('SELECT hostName, contactGroup FROM [DataBase].[dbo].[TableName] WHERE hostName in %s' % sServerNameList)
            server_owner_list = [dict(row) for row in server_owner_result]
        owner_list = [i.get('contactGroup', None) for i in server_owner_list] # Get contact group of the servers
        owner_list = list(set(owner_list))  # remove duplicate server name
        print(owner_list)

        for sOwner in owner_list:
            temp_server_list = dict()
            for row in server_owner_list:
                if row['contactGroup'] == sOwner:
                    temp_server_list[row['hostName']] = disabled_server_list[row['hostName']]

            if len(temp_server_list) > 0:
                send_email(f'{sOwner}@', sSubject, temp_server_list)

except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(f'Other error occurred: {e} {exc_type} {fname} {exc_tb.tb_lineno}')
