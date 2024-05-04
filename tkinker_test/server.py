import time
import zmq
import json

context = zmq.Context()
socket = context.socket(zmq.REP)
print("Starting Server")
socket.bind("tcp://*:5555")

while True:
    #  Wait for next request from client
    message = str(socket.recv_string())
    print("Received request: %s" % message)
    message = json.loads(message)

    action = message["type"]

    path = message["path"]
    path = path.split("/")
    location = path[0]
    spec = path[1]

    incoming_data = message["data"]

    file = open("tasks.json")
    server_data = json.load(file)

    match action:
        case "get":
            match location:
                case "tasks":
                    match spec:
                        case "all":
                            response = server_data["tasks"]
                        case spec if spec.isdigit():
                            print(server_data["tasks"][int(spec)-1])
                            response = server_data["tasks"][int(spec)-1]
                        case _:
                            response = 400
                case "attributes":
                    match spec:
                        case "all":
                            response = server_data["attributes"]
                        case spec if spec.isdigit():
                            response = server_data["attributes"][int(spec) - 1]
        case "post":
            print("Push")
        case "put":
            print("Put")


    #  Do some 'work'
    time.sleep(1)

    #  Send reply back to client
    socket.send_string(json.dumps({"response": response}))
