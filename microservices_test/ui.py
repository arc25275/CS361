from time import sleep
import webbrowser

PRNG_FILE = "prng-service.txt"
IMG_FILE = "img-service.txt"


while True:
    text_input = input("Type 1 to receive a random image, or 2 to exit.\n")
    if text_input == "1":
        # Normal opening and closing didn't work correctly for me (Was not writing on time/other issues)
        # so I switched to this.
        with open(PRNG_FILE, "w") as prng_service:
            prng_service.write("run")
        sleep(5)
        with open(PRNG_FILE, "r+") as prng_service:
            rng = prng_service.read()
            prng_service.seek(0)
            prng_service.truncate(0)
        print("Random Number:", rng)
        with open(IMG_FILE, "w") as img_service:
            img_service.write(rng)
        sleep(5)
        with open(IMG_FILE, "r+") as img_service:
            img_path = img_service.read()
            print("Image Path:", img_path)
            webbrowser.open(img_path)
            img_service.seek(0)
            img_service.truncate(0)
    elif text_input == "2":
        break
    else:
        print("Invalid option")
