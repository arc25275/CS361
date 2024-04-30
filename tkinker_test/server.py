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

    file = open("tasks.json")
    data = json.load(file)

    match message:
        case "all":
            response = data
        case message if message.isdigit():
            print(data["tasks"][int(message)-1])
            response = data["tasks"][int(message)-1]
        case _:
            response = 400

    #  Do some 'work'
    time.sleep(1)

    #  Send reply back to client
    socket.send_string(json.dumps({"response": response}))
