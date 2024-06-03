import zmq
import json

context = zmq.Context()
ui_socket = context.socket(zmq.REP)
print("Starting Sorting Microservice")
ui_socket.bind("tcp://*:6666")

server_socket = context.socket(zmq.REQ)
print("Connecting to Server")
server_socket.connect("tcp://localhost:5555")

while True:
    #  Wait for next request from client
    message = str(ui_socket.recv_string())
    print(f"Received request: {message}")
    message = json.loads(message)
    type = message["type"]
    limiter = message["limiter"]
    attr = message["attr"]
    if limiter == "":
        ui_socket.send_string(json.dumps({"code": 400, "message": "Invalid Request", "data": None}))
        continue
    if type == "sort":
        order = message["order"]
        server_socket.send_string(json.dumps({"type": "get", "path": "tasks/all", "data": None}))
        response = server_socket.recv_string()
        response = json.loads(response)
        if response["code"] == 200:
            tasks = response["data"]
            extra_tasks = []
            if attr:
                tasks_with_attr = []
                for task in tasks:
                    for attribute in task["attributes"]:
                        if attribute["name"] == limiter:
                            value = int(attribute["value"]) if attribute["value"].isdigit() else attribute["value"]
                            tasks_with_attr.append({value: task})
                            break
                    else:
                        extra_tasks.append(task["id"])


                tasks = sorted(tasks_with_attr, key=lambda x: list(x.keys())[0])
                id_list = []
                for task in tasks:
                    id_list.append(list(task.values())[0]["id"])

            else:
                tasks = sorted(tasks, key=lambda x: x[limiter])
                id_list = []
                for task in tasks:
                    id_list.append(task["id"])
            id_list += extra_tasks
            if order == "desc":
                id_list = id_list[::-1]

            ui_socket.send_string(json.dumps({"code": 200, "message": "Sorted", "data": id_list}))
        else:
            ui_socket.send_string(json.dumps(response))
    elif type == "filter":
        filter = message["filter"]
        server_socket.send_string(json.dumps({"type": "get", "path": "tasks/all", "data": None}))
        response = server_socket.recv_string()
        response = json.loads(response)
        if response["code"] == 200:
            tasks = response["data"]
            filtered = []
            if attr:
                for task in tasks:
                    for attribute in task["attributes"]:
                        if attribute["name"] == limiter and attribute["value"] == filter:
                            filtered.append(task)
                            break
            else:
                for task in tasks:
                    if str(task[limiter]) == filter:
                        filtered.append(task)
            id_list = []
            for task in filtered:
                id_list.append(task["id"])
            ui_socket.send_string(json.dumps({"code": 200, "message": "Filtered", "data": id_list}))
        else:
            ui_socket.send_string(json.dumps(response))
    else:
        ui_socket.send_string(json.dumps({"code": 400, "message": "Invalid Request", "data": None}))
