import json
import http.client

from pick import pick

host = '127.0.0.1'
port = 9000

# Connection
conn = http.client.HTTPConnection(host, port)

# Choose the action
options = ['START', 'STOP', 'CHECK']
option, index = pick(options, '')

# Setting up the request
if index == 0:
    with open("./default_module_config.json") as json_file:
        request_dict = json.load(json_file)
    params = json.dumps(request_dict)
    headers = {'Content-type': 'application/json'}
    # Sending the request message
    conn.request("POST", '/start', params, headers)

elif index == 1:
    params = json.dumps({ 'message': option })
    headers = {'Content-type': 'application/json'}
    # Sending the request message
    conn.request("POST", '/stop', params, headers)

elif index == 2:
    params = json.dumps({ 'message': option })
    headers = {'Content-type': 'application/json'}
    # Sending the request message
    conn.request("POST", '/check', params, headers)

else:
    raise IndexError

# Response received
print('Response')
res = conn.getresponse()
print(res.status, res.reason)
data = res.read().decode('utf-8')
response_string = str(data)
response = json.loads(response_string)
print(json.dumps(response, indent = 4, sort_keys=False))

# Close
conn.close()