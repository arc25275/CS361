from time import sleep
import os

IMG_FILE = "img-service.txt"
IMG_DIRECTORY = "C:/Users/arc25/PycharmProjects/CS361/microservices_test/flowers/"

while True:
    sleep(1)
    with open(IMG_FILE, "r+") as img_service:
        num = img_service.read()
        if num.isdigit():
            sleep(2)
            img_num = int(num) % 211
            img_num = str(img_num).zfill(4)  # Add zeros to front
            path = os.path.join(IMG_DIRECTORY, img_num + ".png")
            img_service.seek(0)
            img_service.truncate(0)
            img_service.write(path)
            print("Generated Image Path:", path)
