// Signal K application template file.
//
// This application demonstrates core SensESP concepts in a very
// concise manner. You can build and upload the application as is
// and observe the value changes on the serial port monitor.
//
// You can use this source file as a basis for your own projects.
// Remove the parts that are not relevant to you, and add your own code
// for external hardware libraries.

#include <memory>

#include <Wire.h>
#include "HT_SSD1306Wire.h"   // OLED Display Library
#include "sensesp.h"
#include "sensesp/sensors/analog_input.h"
#include "sensesp/sensors/digital_input.h"
#include "sensesp/sensors/sensor.h"
#include "sensesp/signalk/signalk_output.h"
#include "sensesp/signalk/signalk_put_request_listener.h"
#include "sensesp/system/lambda_consumer.h"
#include "sensesp_app_builder.h"

#include "chain_counter.h"


using namespace sensesp;

// Global variables to store sensor values for display
float current_analog_value1 = 0.0;
float current_analog_value2 = 0.0;
float current_analog_value3 = 0.0;
bool current_digital_input1 = false;
bool current_digital_input2 = false;
bool display_working = false;

// GPIO numbers (NOT PIN NUMBERS) to use for the analog inputs
const uint8_t kAnalogInput1Gpio = 7;
const uint8_t kAnalogInput2Gpio = 6;
const uint8_t kAnalogInput3Gpio = 5;

// Define how often (in milliseconds) new samples are acquired
const unsigned int kAnalogInputReadInterval = 500;

// Define the produced value at the maximum input voltage (3.3V).
// A value of 3.3 gives output equal to the input voltage.
const float kAnalogInputScale = 3.3;

// Digital input GPIO numbers (NOT PIN NUMBERS) and interval
const uint8_t kDigitalInput1Gpio = 4;
const uint8_t kDigitalInput2Gpio = 3;
const unsigned int kDigitalInputReadInterval = 500;

// Windlass chain counter GPIOs. Override with -D CHAIN_*_GPIO=n in
// platformio.ini if these clash with your wiring. All three inputs must be
// level shifted or opto-isolated: the windlass harness is 12 V and the ESP32
// is 3.3 V tolerant only.
#ifndef CHAIN_SENSOR_GPIO
#define CHAIN_SENSOR_GPIO 38
#endif
#ifndef CHAIN_UP_GPIO
#define CHAIN_UP_GPIO 39
#endif
#ifndef CHAIN_DOWN_GPIO
#define CHAIN_DOWN_GPIO 40
#endif

const uint8_t kChainSensorGpio = CHAIN_SENSOR_GPIO;
const uint8_t kChainUpGpio = CHAIN_UP_GPIO;
const uint8_t kChainDownGpio = CHAIN_DOWN_GPIO;

// Chain paid out per counted pulse, in meters. This is a starting point for a
// Quick Eagle gypsy counting both sensor edges; calibrate it against a marked
// chain and set the real value in the web config UI.
const float kChainDistancePerPulse = 0.1675;

// Signal K path the rode length is published on and accepts PUT requests for.
// Not part of the Signal K schema -- there is no windlass or rode key in it --
// but it sits in the navigation.anchor tree the dashboard already reads. Change
// it in the web config UI if your consumer expects something else.
const char* kRodeSkPath = "navigation.anchor.rodeDeployed";

// Values mirrored to the OLED.
float current_rode = 0.0;
int current_pulse_count = 0;
bool current_chain_up = false;
bool current_chain_down = false;

// Test this yourself by connecting pin 15 to pin 14 with a jumper wire and
// see if the value changes!

// Function to scan I2C bus for devices
void scanI2C() {
  Serial.println("Scanning I2C bus...");
  int deviceCount = 0;
  
  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    byte error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.printf("I2C device found at address 0x%02X\n", address);
      deviceCount++;
    }
  }
  
  if (deviceCount == 0) {
    Serial.println("No I2C devices found!");
  } else {
    Serial.printf("Found %d I2C device(s)\n", deviceCount);
  }
}

// OLED Display Definition (try both 0x3C and 0x3D addresses)
static SSD1306Wire display(0x3c, 500000, SDA_OLED, SCL_OLED, GEOMETRY_128_64, RST_OLED);

// The setup function performs one-time application initialization.
void setup() {
  SetupLogging(ESP_LOG_DEBUG);

  // Construct the global SensESPApp() object
  SensESPAppBuilder builder;
  sensesp_app = (&builder)
                    // Set a custom hostname for the app.
                    ->set_hostname("my-sensesp-project")
                    // Optionally, hard-code the WiFi and Signal K server
                    // settings. This is normally not needed.
                    //->set_wifi_client("My WiFi SSID", "my_wifi_password")
                    //->set_wifi_access_point("My AP SSID", "my_ap_password")
                    //->set_sk_server("192.168.10.3", 80)
                    ->get_app();

  // Create three Analog Input Sensors that read analog input pins
  // periodically.
  pinMode(kAnalogInput1Gpio, INPUT);
  auto analog_input1 = std::make_shared<AnalogInput>(
      kAnalogInput1Gpio, kAnalogInputReadInterval, "", kAnalogInputScale);

  pinMode(kAnalogInput2Gpio, INPUT);
  auto analog_input2 = std::make_shared<AnalogInput>(
      kAnalogInput2Gpio, kAnalogInputReadInterval, "", kAnalogInputScale);

  pinMode(kAnalogInput3Gpio, INPUT);
  auto analog_input3 = std::make_shared<AnalogInput>(
      kAnalogInput3Gpio, kAnalogInputReadInterval, "", kAnalogInputScale);

  // Add observers that print out the current values of the analog inputs
  // every time they change and store them for display.
  analog_input1->attach([analog_input1]() {
    current_analog_value1 = analog_input1->get();
    debugD("Analog input 1 (GPIO %d) value: %.2fV", kAnalogInput1Gpio, current_analog_value1);
  });

  analog_input2->attach([analog_input2]() {
    current_analog_value2 = analog_input2->get();
    debugD("Analog input 2 (GPIO %d) value: %.2fV", kAnalogInput2Gpio, current_analog_value2);
  });

  analog_input3->attach([analog_input3]() {
    current_analog_value3 = analog_input3->get();
    debugD("Analog input 3 (GPIO %d) value: %.2fV", kAnalogInput3Gpio, current_analog_value3);
  });

  // Create two Digital Input Sensors that read digital input pins
   auto digital_input1 = std::make_shared<DigitalInputChange>(
      kDigitalInput1Gpio, INPUT_PULLUP, CHANGE);
    auto digital_input2 = std::make_shared<DigitalInputChange>(
      kDigitalInput2Gpio, INPUT_PULLUP, CHANGE);

  // Add observers that print out the current values of the digital inputs
  digital_input1->attach([digital_input1]() {
    current_digital_input1 = digital_input1->get();
    debugD("Digital input 1 value: %d", current_digital_input1);
  });
  digital_input2->attach([digital_input2]() {
    current_digital_input2 = digital_input2->get();
    debugD("Digital input 2 value: %d", current_digital_input2);
  });

  // Configure digital inputs
  pinMode(kDigitalInput1Gpio, INPUT_PULLDOWN);
  pinMode(kDigitalInput2Gpio, INPUT_PULLDOWN);

  // Connect the digital inputs to LambdaConsumers that print the value when it changes.
  auto digital_input1_consumer = std::make_shared<LambdaConsumer<bool>>(
      [](bool input) { 
        current_digital_input1 = input;
        debugD("Digital input 1 (GPIO %d) value changed: %d", kDigitalInput1Gpio, input);
      });
  digital_input1->connect_to(digital_input1_consumer);
  auto digital_input2_consumer = std::make_shared<LambdaConsumer<bool>>(
      [](bool input) { 
        current_digital_input2 = input;
        debugD("Digital input 2 (GPIO %d) value changed: %d", kDigitalInput2Gpio, input);
      });
  digital_input2->connect_to(digital_input2_consumer);
  
  // Configure signalk outputs for the analog inputs
  // Analog Input 1
  auto ai1_metadata = std::make_shared<SKMetadata>("V", "Analog input 1 voltage");
  auto ai1_sk_output = std::make_shared<SKOutput<float>>(
      "sensors.analog_input1.voltage",   // Signal K path
      "/Sensors/Analog Input 1/Voltage",  // configuration path
      ai1_metadata
  );
  ConfigItem(ai1_sk_output)
      ->set_title("Analog Input 1 Voltage SK Output Path")
      ->set_description("The SK path to publish the analog input 1 voltage")
      ->set_sort_order(100);
  analog_input1->connect_to(ai1_sk_output);

  // Analog Input 2
  auto ai2_metadata = std::make_shared<SKMetadata>("V", "Analog input 2 voltage");
  auto ai2_sk_output = std::make_shared<SKOutput<float>>(
      "sensors.analog_input2.voltage",   // Signal K path
      "/Sensors/Analog Input 2/Voltage",  // configuration path
      ai2_metadata
  );
  ConfigItem(ai2_sk_output)
      ->set_title("Analog Input 2 Voltage SK Output Path")
      ->set_description("The SK path to publish the analog input 2 voltage")
      ->set_sort_order(110);
  analog_input2->connect_to(ai2_sk_output);

  // Analog Input 3
  auto ai3_metadata = std::make_shared<SKMetadata>("V", "Analog input 3 voltage");
  auto ai3_sk_output = std::make_shared<SKOutput<float>>(
      "sensors.analog_input3.voltage",   // Signal K path
      "/Sensors/Analog Input 3/Voltage",  // configuration path
      ai3_metadata
  );
  ConfigItem(ai3_sk_output)
      ->set_title("Analog Input 3 Voltage SK Output Path")
      ->set_description("The SK path to publish the analog input 3 voltage")
      ->set_sort_order(120);
  analog_input3->connect_to(ai3_sk_output);

  // Connect digital input 1 to Signal K output.
  auto di1_metadata = std::make_shared<SKMetadata>("", "Digital input 1 value");
  auto di1_sk_output = std::make_shared<SKOutput<bool>>(
      "sensors.digital_input1.value",    // Signal K path
      "/Sensors/Digital Input 1/Value",  // configuration path
      di1_metadata
  );
  ConfigItem(di1_sk_output)
      ->set_title("Digital Input 1 SK Output Path")
      ->set_sort_order(200);

  digital_input1->connect_to(di1_sk_output);

  // Connect digital input 2 to Signal K output.
  auto di2_metadata = std::make_shared<SKMetadata>("", "Digital input 2 value");
  auto di2_sk_output = std::make_shared<SKOutput<bool>>(
      "sensors.digital_input2.value",    // Signal K path
      "/Sensors/Digital Input 2/Value",  // configuration path
      di2_metadata
  );
  ConfigItem(di2_sk_output)
      ->set_title("Digital Input 2 SK Output Path")
      ->set_sort_order(210);
  digital_input2->connect_to(di2_sk_output);

  // Windlass chain counter. The gypsy sensor only reports movement, so the up
  // and down contactor sense lines supply the direction.
  auto chain_counter = std::make_shared<ChainCounter>(
      kChainSensorGpio, kChainUpGpio, kChainDownGpio, kChainDistancePerPulse,
      "/Windlass/Chain Counter");
  ConfigItem(chain_counter)
      ->set_title("Windlass Chain Counter")
      ->set_description(
          "Rode calibration and counter state. Set the pulse count to 0 with "
          "the anchor fully home.")
      ->set_sort_order(300);

  chain_counter->attach([chain_counter]() {
    current_rode = chain_counter->get_rode();
    current_pulse_count = chain_counter->get_pulse_count();
    current_chain_up = chain_counter->get_up();
    current_chain_down = chain_counter->get_down();
    debugD("Rode: %.2fm (%d pulses, dir %d)", current_rode,
           current_pulse_count, chain_counter->get_direction());
  });

  // Deployed rode, in meters.
  auto rode_metadata =
      std::make_shared<SKMetadata>("m", "Anchor rode deployed");
  auto rode_sk_output = std::make_shared<SKOutput<float>>(
      kRodeSkPath,                 // Signal K path
      "/Windlass/Rode Deployed",   // configuration path
      rode_metadata
  );
  ConfigItem(rode_sk_output)
      ->set_title("Rode Deployed SK Output Path")
      ->set_description("The SK path to publish the deployed rode length")
      ->set_sort_order(310);
  chain_counter->connect_to(rode_sk_output);

  // Raw pulse count, mostly useful for calibration.
  auto pulse_metadata =
      std::make_shared<SKMetadata>("", "Windlass gypsy pulse count");
  auto pulse_sk_output = std::make_shared<SKOutput<int>>(
      "sensors.windlass.pulseCount",  // Signal K path
      "/Windlass/Pulse Count",        // configuration path
      pulse_metadata
  );
  ConfigItem(pulse_sk_output)
      ->set_title("Windlass Pulse Count SK Output Path")
      ->set_sort_order(320);
  chain_counter->pulse_count_output()->connect_to(pulse_sk_output);

  // Contactor state, so the dashboard can tell hauling from veering.
  auto up_metadata = std::make_shared<SKMetadata>("", "Windlass hauling up");
  auto up_sk_output = std::make_shared<SKOutput<bool>>(
      "sensors.windlass.up",   // Signal K path
      "/Windlass/Up",          // configuration path
      up_metadata
  );
  ConfigItem(up_sk_output)
      ->set_title("Windlass Up SK Output Path")
      ->set_sort_order(330);
  chain_counter->up_output()->connect_to(up_sk_output);

  auto down_metadata = std::make_shared<SKMetadata>("", "Windlass veering down");
  auto down_sk_output = std::make_shared<SKOutput<bool>>(
      "sensors.windlass.down",  // Signal K path
      "/Windlass/Down",         // configuration path
      down_metadata
  );
  ConfigItem(down_sk_output)
      ->set_title("Windlass Down SK Output Path")
      ->set_sort_order(340);
  chain_counter->down_output()->connect_to(down_sk_output);

  // Accept a Signal K PUT on the rode path so the counter can be zeroed or
  // corrected from the dashboard: PUT 0 with the anchor home.
  auto rode_put_listener =
      std::make_shared<FloatSKPutRequestListener>(kRodeSkPath);
  auto rode_put_consumer = std::make_shared<LambdaConsumer<float>>(
      [chain_counter](float rode) {
        debugI("Rode set to %.2fm over Signal K PUT", rode);
        chain_counter->set_rode(rode);
      });
  rode_put_listener->connect_to(rode_put_consumer);

  // Enable Vext power for peripherals (CRITICAL for Heltec V3!)
  pinMode(Vext, OUTPUT);
  digitalWrite(Vext, LOW);  // LOW = enable power to external components
  delay(500);  // Give power time to stabilize
  display_working = display.init();
  debugD("Standard init: %s\n", display_working ? "SUCCESS" : "FAILED");

  // Scan for devices after successful init
  scanI2C();
  
  // Test display functionality
  display.clear();
  display.setFont(ArialMT_Plain_10);
  display.setTextAlignment(TEXT_ALIGN_LEFT);
  display.drawString(0, 0, "Heltec V3");
  display.drawString(0, 12, "Display Test");
  display.drawString(0, 24, "Init: OK");
  display.setFont(ArialMT_Plain_16);
  display.setTextAlignment(TEXT_ALIGN_CENTER);
  display.drawString(64, 45, "WORKING!");
  display.display();
  Serial.println("Display content updated");

  // To avoid garbage collecting all shared pointers created in setup(),
  // loop from here.
  while (true) {
    loop();
  }
}

void loop() {
  event_loop()->tick(); 
  
  static unsigned long lastDisplayUpdate = 0;
  
  // Update display every 1 second if working
  if (display_working && millis() - lastDisplayUpdate > 1000) {
    lastDisplayUpdate = millis();
    
    // Clear and set up display
    display.clear();
    display.setFont(ArialMT_Plain_10);
    display.setTextAlignment(TEXT_ALIGN_LEFT);
    
    // Rode, direction and raw pulse count on the top line
    const char* chain_dir = current_chain_up     ? "UP"
                            : current_chain_down ? "DN"
                                                 : "--";
    display.drawString(0, 0, "Rode " + String(current_rode, 1) + "m " + chain_dir);
    display.setTextAlignment(TEXT_ALIGN_RIGHT);
    display.drawString(128, 0, "p" + String(current_pulse_count));
    display.setTextAlignment(TEXT_ALIGN_LEFT);
    
    // Analog input values with pin numbers
    display.drawString(0, 10, "A" + String(kAnalogInput1Gpio) + ": " + String(current_analog_value1, 2) + "V");
    display.drawString(0, 20, "A" + String(kAnalogInput2Gpio) + ": " + String(current_analog_value2, 2) + "V");
    display.drawString(0, 30, "A" + String(kAnalogInput3Gpio) + ": " + String(current_analog_value3, 2) + "V");
    
    // Digital input values with pin numbers
    String digital1_str = current_digital_input1 ? "HIGH" : "LOW";
    display.drawString(0, 40, "D" + String(kDigitalInput1Gpio) + ": " + digital1_str);
    
    String digital2_str = current_digital_input2 ? "HIGH" : "LOW";
    display.drawString(0, 50, "D" + String(kDigitalInput2Gpio) + ": " + digital2_str);

    // Uptime in bottom right
    display.setTextAlignment(TEXT_ALIGN_RIGHT);
    display.drawString(128, 54, String(millis()/1000) + "s");
    
    display.display();
    
    // Also output to serial for debugging
    debugD("Display: A%d=%.2fV, A%d=%.2fV, A%d=%.2fV, D%d=%s, D%d=%s, rode=%.2fm (%d pulses, %s)", 
           kAnalogInput1Gpio, current_analog_value1,
           kAnalogInput2Gpio, current_analog_value2, 
           kAnalogInput3Gpio, current_analog_value3,
           kDigitalInput1Gpio, current_digital_input1 ? "HIGH" : "LOW",
           kDigitalInput2Gpio, current_digital_input2 ? "HIGH" : "LOW",
           current_rode, current_pulse_count, chain_dir);
  }
  
  // 1 ms, not 100 ms: the chain counter polls its sensor every 5 ms and a
  // 10 Hz event loop would miss pulses. Still yields to the idle task.
  delay(1);
}

