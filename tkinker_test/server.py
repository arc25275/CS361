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
    print(f"Received request: {message}")
    message = json.loads(message)

    action = message["type"]

    path = message["path"]
    path = path.split("/")
    location = path[0]
    if path != "post":
        spec = path[1]
    else:
        spec = ""
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
            print("Post")
            match location:
                case "tasks":
                    server_data["tasks"].append(incoming_data)
                    response = 200
                case "attributes":
                    server_data["attributes"].append(incoming_data)
                    response = 200
                case _:
                    response = 400
        case "put":
            print("Put")
            match location:
                case "tasks":
                    match spec:
                        case "all":
                            response = 400
                        case spec if spec.isdigit():
                            task_index = int(spec) - 1
                            # Get the existing task
                            server_data["tasks"][task_index].update(incoming_data)
                            response = 200
                        case _:
                            response = 400
        case "delete":
            print("Delete")
            match location:
                case "tasks":
                    match spec:
                        case "all":
                            server_data["tasks"] = []
                            response = 200
                        case spec if spec.isdigit():
                            task_index = int(spec) - 1
                            del server_data["tasks"][task_index]
                            response = 200
                        case _:
                            response = 400
                case "attributes":
                    match spec:
                        case "all":
                            server_data["attributes"] = []
                            response = 200
                        case spec if spec.isdigit():
                            attribute_index = int(spec) - 1
                            del server_data["attributes"][attribute_index]
                            response = 200
                        case _:
                            response = 400
        case _:
            response = 400

    file = open("tasks.json", "w")
    json.dump(server_data, file, indent=4)
    file.close()

    #  Do some 'work'
    time.sleep(1)

    #  Send reply back to client
    socket.send_string(json.dumps({"response": response}))
