import wget
import os
import requests

#Variables in Source Repo
src_user_name = 'admin'
src_passwd = 'admin123'
src_repo = 'releases'


#Variables in Dest Repo
dest_user_name = 'admin'
dest_passwd = 'admin123'
dest_repo = 'Copy'
dest_url = 'http://localhost:8081/service/rest/v1/components?repository=' + dest_repo

# Nexus REST API uses pagination when returning large data. We'll need to know if there is a continuation token to know if we need to send a new get request.
# There will NOT be a token on the first and last requests, so we are using a flag to know if we should make another request or not.
nx_token = None
read_again = True

while read_again == True:
    src_url = 'http://localhost:8081/service/rest/v1/components?repository=' + src_repo
    if not ( nx_token is None):
        src_url = src_url + "&continuationToken=" + nx_token
    
    #Now we are using Requests Library GET method to get a list of components for the 'src_repo'
    resp = requests.get(src_url, auth=(src_user_name, src_passwd))

    # uncomment print statement to get print out of entire JSON being returned by request
    # print resp.json()

    nx_token = resp.json()['continuationToken']

    # the 'items' array in the JSON are the components in the Repository
    components = resp.json()['items']

    for component in components:
    
        # need to gather data to upload file
        group_id = component['group']
        artifact_id = component['name']
        version = component['version']

        # output message to let end user know that we found a component
        print ("Found Component with Group ID " + group_id + ", Artifact ID " + artifact_id + " and version " + version)

        #Since using the post method from the requests library is not working we'll instead build a curl command to then pass the OS to execute and upload the asset(s).
        curl_command = "curl -v -u " + dest_user_name +":" + dest_passwd + " -X POST '" + dest_url + "' -F maven2.groupId=" + group_id + " -F maven2.artifactId=" + artifact_id + " -F maven2.version=" + version

        #let's use a counter to help keep track of asset, also will use when uploding assets. 
        counter = 1

        # we are going to create the POM automatically unless we find one. Need to keep track if we find one
        pom_in_component = False

        # the 'assets' array inside each 'item' are the assets for the current component
        for asset in component['assets']:
        
            asset_url = str(asset['downloadUrl'])
            #debug message to print out the download url from nexus and the current asset #
            #print ('The URL for Asset ' + str(counter) +' is: ' + asset_url)
            if asset_url.endswith('pom'):
                pom_in_component = True

            #we don't want to download or upload md5 or sha1 files
            if not (asset_url.endswith('md5') or asset_url.endswith('sha1') ):

                #We are using wget to download the file as that seems the simplest way. So we need to 'insert' the username and password into the download url
                #using the colon in 'http(s):' to figure out where to insert the username:password
                str_pos = asset_url.find(':')
                # the position will be 3 spots from the colon
                str_pos = str_pos + 3
                http_part = asset_url[0:str_pos]
                rest_of_url = asset_url[str_pos:]
                url_for_download = http_part + src_user_name + ":" + src_passwd + "@" + rest_of_url
                print url_for_download

                my_file = wget.download(url_for_download)
           
                # we need to figure out the file name so we are parsing the download url
                # assuming that anything after the last '/' is the filename

                str_pos = asset_url.rindex('/')
                str_pos = str_pos + 1           
                asset_name = asset_url[str_pos:]
                #print 'the asset name is ' + asset_name

                # we also need the file extension
                #assuming that anything after the last '.' is the extension

                str_pos = asset_name.rindex('.')
                file_ext = asset_name[str_pos + 1:]

                #print 'the file extension is ' + file_ext

                # adding asset details to the curl command
                curl_command = curl_command  + " -F maven2.asset"+ str(counter) + "=@" + asset_name  +  " -F maven2.asset"+ str(counter) + ".extension=" + file_ext
                                         
                counter = counter + 1
            
        if pom_in_component == False:
            curl_command = curl_command + " -F maven2.generate-pom=true"
        #now let's try to upload the file by just passing the curl command to the OS for execution
        print curl_command
        try:
            os.system(curl_command)
        except Exception, e:
                if type(e) == exceptions.OSError and e.errno == 13:
                    print e
                pass

    if ( (nx_token is None)):
        read_again = False
