# Run "pip install Office365-REST-Python-Client" to install the package

from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
domanin = ''
siteName = ''
url = f'https://{domanin}.sharepoint.com/sites/{siteName}'
username = 'username'
password = 'password'

ctx_auth = AuthenticationContext(url)

if ctx_auth.acquire_token_for_user(username, password):
    ctx = ClientContext(url, ctx_auth)
    web = ctx.web
    ctx.load(web)
    ctx.execute_query()
    #print('Authentication Successful for: ',web.properties['Title'])
    target_folder_url= ""
    root_folder= ctx.web.get_folder_by_server_relative_url(target_folder_url)
    root_folder.expand(["Files", "Folders"]).get().execute_query()
    for file in root_folder.files:  # type: File
        if file.name == "":
            ownerList = ((file.read()).decode('utf-8')).split('\r\n')

    for owner in ownerList:
        print(owner)
else:
    print(ctx_auth.get_last_error())
