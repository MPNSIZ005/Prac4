# Import libraries
import RPi.GPIO as GPIO
import random
import ES2EEPROMUtils
import os
import time

# some global variables that need to change as we run the program
end_of_game = False  # set if the user wins or ends the game
guess = 0
value = 1
attempts = 0
pwm_red_led = 0
pwm_buzzer = 0
last_interrupt_time = 0
last_rising_time = 0
# DEFINE THE PINS USED HERE
LED_value = [11, 13, 15]
LED_accuracy = 32
btn_submit = 38
btn_increase = 40
buzzer = 12
eeprom = ES2EEPROMUtils.ES2EEPROM()


# Print the game banner
def welcome():
    os.system('clear')
    print("  _   _                 _                  _____ _            __  __ _")
    print("| \ | |               | |                / ____| |          / _|/ _| |")
    print("|  \| |_   _ _ __ ___ | |__   ___ _ __  | (___ | |__  _   _| |_| |_| | ___ ")
    print("| . ` | | | | '_ ` _ \| '_ \ / _ \ '__|  \___ \| '_ \| | | |  _|  _| |/ _ \\")
    print("| |\  | |_| | | | | | | |_) |  __/ |     ____) | | | | |_| | | | | | |  __/")
    print("|_| \_|\__,_|_| |_| |_|_.__/ \___|_|    |_____/|_| |_|\__,_|_| |_| |_|\___|")
    print("")
    print("Guess the number and immortalise your name in the High Score Hall of Fame!")


def current_milli_time():
    return round(time.time() * 1000)


# Print the game menu
def menu():
    global end_of_game
    option = input("Select an option:   H - View High Scores     P - Play Game       Q - Quit\n")
    option = option.upper()
    if option == "H":
        os.system('clear')
        print("HIGH SCORES!!")
        s_count, ss = fetch_scores()
        display_scores(s_count, ss)
        menu()
    elif option == "P":
        end_of_game = False
        os.system('clear')
        print("Starting a new round!")
        print("Use the buttons on the Pi to make and submit your guess!")
        print("Press and hold the guess button to cancel your game")
        global value
        value = generate_number()
        accuracy_leds()
        while not end_of_game:
            trigger_buzzer()
            
    elif option == "Q":
        print("Come back soon!")
        exit()
    else:
        print("Invalid option. Please select a valid one!")


def display_scores(count, raw_data):
    # print the scores to the screen in the expected format
    print("There are {} scores. Here are the top 3!".format(count))
    #get names and scores
    first_name = raw_data[0][0] + raw_data[0][1]+ raw_data[0][2]
    first_score = raw_data[0][3]
    second_name = raw_data[1][0] + raw_data[1][1]+ raw_data[1][2]
    second_score = raw_data[1][3]
    third_name = raw_data[2][0] + raw_data[2][1]+ raw_data[2][2]
    third_score = raw_data[2][3]
    # print out the scores in the required format
    print("1 - ",first_name,"took", first_score,"guesses")
    print("2 - ",second_name,"took", second_score,"guesses")
    print("3 - ",third_name,"took", third_score,"guesses")


# Setup Pins
def setup():
    # Setup board mode
    GPIO.setmode(GPIO.BOARD) # defined-pins line up to the pin numbers on the board
    # SETUP REGULAR GPIO
        #LEDS
    for i in LED_value:
        GPIO.setup(i, GPIO.OUT)
        GPIO.output(i,GPIO.LOW)
        #BTNS
    GPIO.setup(btn_submit, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(btn_increase, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(btn_increase,GPIO.FALLING,callback=btn_increase_pressed)
    GPIO.add_event_detect(btn_submit,GPIO.RISING,callback=btn_guess_pressed)
    # SETUP PWM CHANNELS
        #RED LED
    GPIO.setup(LED_accuracy, GPIO.OUT)
    global pwm_red_led
    pwm_red_led = GPIO.PWM(LED_accuracy, 1000)  #GPIO.PWM([pin], [frequency])
    pwm_red_led.start(0) # pwm.start([duty cycle])
        #buzzer
    GPIO.setup(buzzer, GPIO.OUT)
    global pwm_buzzer
    pwm_buzzer = GPIO.PWM(buzzer, 500)
    pwm_buzzer.start(0)


# Load high scores
def fetch_scores():
    # get however many scores there are
    score_count = eeprom.read_byte(0)
    # Get the scores and convert code to ascii
    scores = []
    for i in range(score_count):
        data = eeprom.read_block(i+1 , 4)
        data[0] = chr(data[0])
        data[1] = chr(data[1])
        data[2] = chr(data[2])
        scores.append(data)
    # return back the results
    return score_count, scores

# Save high scores
def save_scores():
    # fetch scores
    s_count, ss = fetch_scores()
    # fetch new name and number of attempts
    global attempts
        #get 3 letter name
    name = ""
    while len(name) != 3:
        name = input("please enter a 3 letter name: ")
    new_score = [name[0],name[1],name[2],attempts]
        #reset attempts
    attempts = 0
    # include new score
    ss.append(new_score)
    # sort
    ss.sort(key=lambda x: x[3])
    # update total amount of scores
    eeprom.write_block(0, [s_count])
    # write new scores
    for i, score in enumerate(ss):
            data_to_write = []
            # get the string
            data_to_write.append(ord(score[0]))
            data_to_write.append(ord(score[1]))
            data_to_write.append(ord(score[2]))
            data_to_write.append(score[3])
            eeprom.write_block(i+1, data_to_write)


# Generate guess number
def generate_number():
    return random.randint(0, pow(2, 3)-1)


# Increase button pressed
def btn_increase_pressed(channel):
    
    global last_interrupt_time
    interrupt_time = current_milli_time()
  # If interrupts come faster than 200ms, assume it's a bounce and ignore
    if (interrupt_time - last_interrupt_time > 200):
    # Increase the value shown on the LEDs
    # You can choose to have a global variable store the user's current guess, 
    # or just pull the value off the LEDs when a user makes a guess
        global guess
        guess = guess + 1
        if(guess > 7):
            guess = 0
        set_leds()
        pass
    last_interrupt_time = interrupt_time
    accuracy_leds()


# set Binary LEDS
def set_leds():
    if(guess == 0):
        for i in LED_value:
            GPIO.output(i,GPIO.LOW)
    elif(guess == 1):
        GPIO.output(11, GPIO.HIGH)
    elif(guess == 2):
        GPIO.output(11, GPIO.LOW)
        GPIO.output(13, GPIO.HIGH)
    elif(guess == 3):
        GPIO.output(11, GPIO.HIGH)
    elif(guess == 4):
        GPIO.output(11, GPIO.LOW)
        GPIO.output(13, GPIO.LOW)
        GPIO.output(15, GPIO.HIGH)
    elif(guess == 5):
        GPIO.output(11, GPIO.HIGH)
    elif(guess == 6):
        GPIO.output(11, GPIO.LOW)
        GPIO.output(13, GPIO.HIGH)
    elif(guess == 7):
        GPIO.output(11, GPIO.HIGH)
        GPIO.output(13, GPIO.HIGH)


# Guess button
def btn_guess_pressed(channel):
    global last_interrupt_time
    global end_of_game
    global value
    global attempts
    interrupt_time = current_milli_time()

  # If interrupts come faster than 200ms, assume it's a bounce and ignore
    if (interrupt_time - last_interrupt_time > 200 and not end_of_game):
        #increase attempts
        attempts += 1
        print("checking guess..")
        time.sleep(2)
        # If they've pressed and held the button, clear up the GPIO and take them back to the menu screen
        if(GPIO.input(btn_submit) == 1):
            end_of_game = True
            attempts = 0
            GPIO.output(11, GPIO.LOW)
            GPIO.output(13, GPIO.LOW)
            GPIO.output(15, GPIO.LOW)
            pwm_red_led.ChangeDutyCycle(0)
            pwm_buzzer.ChangeDutyCycle(0)
            return
        # Compare the actual value with the user value displayed on the LEDs
        if(guess == value):
        # if it's an exact guess:
        # - Disable LEDs and Buzzer
        # - tell the user and prompt them for a name
        # - fetch all the scores
        # - add the new score
        # - sort the scores
        # - Store the scores back to the EEPROM, being sure to update the score count
            GPIO.output(11, GPIO.LOW)
            GPIO.output(13, GPIO.LOW)
            GPIO.output(15, GPIO.LOW)
            pwm_red_led.ChangeDutyCycle(0)
            pwm_buzzer.ChangeDutyCycle(0)
            end_of_game = True
            print("correct")
            save_scores()
        # Change the PWM LED
        # if it's close enough, adjust the buzzer
        else:            
            value = generate_number()
            accuracy_leds
            print("false, try again")     
    last_interrupt_time = current_milli_time()

# LED Brightness
def accuracy_leds():  
    #pwm_red_led.ChangeDutyCycle(100) # 0-100%
    # Set the brightness of the LED based on how close the guess is to the answer
    # - The % brightness should be directly proportional to the % "closeness"
    # - For example if the answer is 6 and a user guesses 4, the brightness should be at 4/6*100 = 66%
    # - If they guessed 7, the brightness would be at ((8-7)/(8-6)*100 = 50%
    #  

    offset = abs(value - guess)
    if offset > 4:
        offset = abs(8-offset)
    brightness = (1 - offset/5) * 100
    # if(guess > value):
    #     brightness = (8-guess)/(8-value) * 100
    # else:
    #     brightness = (8-value)/(8-guess) * 100
    pwm_red_led.ChangeDutyCycle(brightness)


# Sound Buzzer for 100 miliseconds
def buzz():
    pwm_buzzer.ChangeDutyCycle(50)
    time.sleep(0.2)
    pwm_buzzer.ChangeDutyCycle(0)

def trigger_buzzer():
    # The buzzer operates differently from the LED
    # While we want the brightness of the LED to change(duty cycle), we want the frequency of the buzzer to change
    # The buzzer duty cycle should be left at 50%
    # If the user is off by an absolute value of 3, the buzzer should sound once every second
    # If the user is off by an absolute value of 2, the buzzer should sound twice every second
    # If the user is off by an absolute value of 1, the buzzer should sound 4 times a second
    offset = abs(value - guess)
    if offset > 4:
        offset = abs(8-offset)
    if offset == 3:
        buzz()
        time.sleep(0.9)
    if offset == 2:
        buzz()
        time.sleep(0.4)
        buzz()
        time.sleep(0.4)
    if offset == 1:
        buzz()
        time.sleep(0.25)
        buzz()
        time.sleep(0.25)
        buzz()
        time.sleep(0.25)
    else:
        time.sleep(1)


if __name__ == "__main__":
    #clear and populate eeprom with mock scores
    eeprom.clear(2048)
    eeprom.populate_mock_scores()
    try:
        # Call setup function
        setup()
        welcome()
        while True:
            menu()
    except Exception as e:
        print(e)
    finally:
        GPIO.cleanup()
