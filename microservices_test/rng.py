from time import sleep
import random

PRNG_FILE = "prng-service.txt"

while True:
    sleep(1)
    with open(PRNG_FILE, "r+") as prng_service:
        val = prng_service.read()
        if val == "run":
            sleep(2)
            rand_val = str(random.randint(1, 500))
            prng_service.seek(0)
            prng_service.truncate(0)
            prng_service.write(rand_val)
            print("Generated Random Number:", rand_val)