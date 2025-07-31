import RPi.GPIO as GPIO

class GPIOControl:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        self.setup_pins()

    def setup_pins(self):
        self.engine_power_pin = 17  # Example GPIO pin for engine power
        self.stage_decouple_pin = 27  # Example GPIO pin for stage decoupling
        self.rcs_activation_pin = 22  # Example GPIO pin for RCS activation
        self.sas_activation_pin = 23  # Example GPIO pin for SAS activation

        GPIO.setup(self.engine_power_pin, GPIO.OUT)
        GPIO.setup(self.stage_decouple_pin, GPIO.OUT)
        GPIO.setup(self.rcs_activation_pin, GPIO.OUT)
        GPIO.setup(self.sas_activation_pin, GPIO.OUT)

    def set_engine_power(self, state):
        GPIO.output(self.engine_power_pin, state)

    def decouple_stage(self):
        GPIO.output(self.stage_decouple_pin, GPIO.HIGH)
        GPIO.output(self.stage_decouple_pin, GPIO.LOW)

    def activate_rcs(self):
        GPIO.output(self.rcs_activation_pin, GPIO.HIGH)

    def deactivate_rcs(self):
        GPIO.output(self.rcs_activation_pin, GPIO.LOW)

    def activate_sas(self):
        GPIO.output(self.sas_activation_pin, GPIO.HIGH)

    def deactivate_sas(self):
        GPIO.output(self.sas_activation_pin, GPIO.LOW)

    def cleanup(self):
        GPIO.cleanup()