import json
import csv
import zmq

context = zmq.Context()
socket = context.socket(zmq.REP)
print("Starting Server")
socket.bind("tcp://*:7777")

while True:
    #  Wait for next request from client
    message = str(socket.recv_string())
    print(f"Received request: {message}")
    if message != "export":
        socket.send_string(json.dumps({"code": 400, "message": "Invalid Request", "data": None}))
        continue

    with open("../data.csv", "w", newline="") as file:
        writer = csv.writer(file)
        with open("../microservice_B/data.json") as json_file:
            data = json.load(json_file)
            fields = ["ID", "Name", "Date", "Description"]
            for attribute in data["attributes"]:
                if attribute["name"] not in fields:
                    fields.append(attribute["name"])
            writer.writerow(fields)
            for task in data["tasks"]:
                row = [task["id"], task["name"], task["date"], task["description"]]
                for attribute in data["attributes"]:
                    value = ""
                    for attr in task["attributes"]:
                        if attr["name"] == attribute["name"]:
                            value = attr["value"]
                            break
                    row.append(value)
                writer.writerow(row)
    socket.send_string(json.dumps({"code": 200, "message": "Exported", "data": None}))