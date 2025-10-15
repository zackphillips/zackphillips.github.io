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
#include "sensesp/system/lambda_consumer.h"
#include "sensesp_app_builder.h"


using namespace sensesp;

// Global variables to store sensor values for display
float current_analog_value = 0.0;
bool current_digital_input1 = false;
bool current_digital_input2 = false;
bool display_working = false;

// GPIO number (NOT PIN NUMBER) to use for the analog input
const uint8_t kAnalogInputPin = 7;

// Define how often (in milliseconds) new samples are acquired
const unsigned int kAnalogInputReadInterval = 500;

// Define the produced value at the maximum input voltage (3.3V).
// A value of 3.3 gives output equal to the input voltage.
const float kAnalogInputScale = 3.3;

// Digital output GPIO number (NOT PIN NUMBER) and interval
const uint8_t kDigitalOutputPin = 6;
const unsigned int kDigitalOutputInterval = 650;

// Digital input GPIO numbers (NOT PIN NUMBERS) and interval
const uint8_t kDigitalInput1Pin = 5;
const uint8_t kDigitalInput2Pin = 4;
const unsigned int kDigitalInput2Interval = 1000;

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

  // Create a new Analog Input Sensor that reads an analog input pin
  // periodically.
  pinMode(kAnalogInputPin, INPUT);
  auto analog_input = std::make_shared<AnalogInput>(
      kAnalogInputPin, kAnalogInputReadInterval, "", kAnalogInputScale);

  // Add an observer that prints out the current valu e of the analog input
  // every time it changes and store it for display.
  analog_input->attach([analog_input]() {
    current_analog_value = analog_input->get();
    debugD("Analog input value: %f", current_analog_value);
  });

  // Set GPIO pin to output and toggle it every 650 ms
  pinMode(kDigitalOutputPin, OUTPUT);
  event_loop()->onRepeat(kDigitalOutputInterval, [kDigitalOutputPin]() {
    digitalWrite(kDigitalOutputPin, !digitalRead(kDigitalOutputPin));
  });

  // Read GPIO pin every time it changes
  auto digital_input1 = std::make_shared<DigitalInputChange>(
      kDigitalInput1Pin, INPUT_PULLUP, CHANGE);

  digital_input1->attach([digital_input1]() {
    current_digital_input1 = digital_input1->get();
    debugD("Digital input 1 value: %d", current_digital_input1);
  });

  // Connect the digital input to a lambda consumer that prints out the
  // value every time it changes.

  auto digital_input1_consumer = std::make_shared<LambdaConsumer<bool>>(
      [](bool input) { 
        current_digital_input1 = input;
        debugD("Digital input value changed: %d", input); 
      });

  digital_input1->connect_to(digital_input1_consumer);

  // Create another digital input, this time with RepeatSensor. This approach
  // can be used to connect external sensor library to SensESP!

  // Configure the pin. Replace this with your custom library initialization
  // code!
  pinMode(kDigitalInput2Pin, INPUT_PULLUP);

  // Define a new RepeatSensor that reads the pin every 100 ms.
  // Replace the lambda function internals with the input routine of your custom
  // library.

  // Again, test this yourself by connecting pin 15 to pin 13 with a jumper
  // wire and see if the value changes!
  auto digital_input2 = std::make_shared<RepeatSensor<bool>>(
      kDigitalInput2Interval,
      [kDigitalInput2Pin]() { return digitalRead(kDigitalInput2Pin); });

  digital_input2->attach([digital_input2]() {
    current_digital_input2 = digital_input2->get();
    debugD("Digital input 2 value: %d", current_digital_input2);
  });

  // Connect the analog input to Signal K output. This will publish the
  // analog input value to the Signal K server every time it changes.
  auto aiv_metadata = std::make_shared<SKMetadata>("V", "Analog input voltage");
  auto aiv_sk_output = std::make_shared<SKOutput<float>>(
      "sensors.analog_input.voltage",   // Signal K path
      "/Sensors/Analog Input/Voltage",  // configuration path, used in the
                                        // web UI and for storing the
                                        // configuration
      aiv_metadata
  );

  ConfigItem(aiv_sk_output)
      ->set_title("Analog Input Voltage SK Output Path")
      ->set_description("The SK path to publish the analog input voltage")
      ->set_sort_order(100);

  analog_input->connect_to(aiv_sk_output);

  // Connect digital input 2 to Signal K output.
  auto di2_metadata = std::make_shared<SKMetadata>("", "Digital input 2 value");
  auto di2_sk_output = std::make_shared<SKOutput<bool>>(
      "sensors.digital_input2.value",    // Signal K path
      "/Sensors/Digital Input 2/Value",  // configuration path
      di2_metadata
  );

  ConfigItem(di2_sk_output)
      ->set_title("Digital Input 2 SK Output Path")
      ->set_sort_order(200);

  digital_input2->connect_to(di2_sk_output);

  debugD("Starting OLED Display Test...");
  
  // Enable Vext power for peripherals (CRITICAL for Heltec V3!)
  pinMode(Vext, OUTPUT);
  digitalWrite(Vext, LOW);  // LOW = enable power to external components
  delay(500);  // Give power time to stabilize
  debugD("Vext power enabled for display");
  debugD("OLED Pins - SDA: %d, SCL: %d, RST: %d\n", SDA_OLED, SCL_OLED, RST_OLED);

  // Try multiple initialization approaches
  debugD("Initializing display...");
  
  // Method 1: Try standard init
  bool initSuccess = display.init();
  display_working = initSuccess;
  debugD("Standard init: %s\n", initSuccess ? "SUCCESS" : "FAILED");

  if (initSuccess) {
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
      
    } else {
      Serial.println("Display init failed - trying recovery...");
      
      // Try manual I2C setup and scan
      Wire.begin(SDA_OLED, SCL_OLED);
      delay(100);
      scanI2C();
      
      // Try different approaches
      Serial.println("Trying alternative initialization...");
      display.end();
      delay(100);
      initSuccess = display.init();
      Serial.printf("Retry init: %s\n", initSuccess ? "SUCCESS" : "FAILED");
    }

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
    
    // Title
    display.drawString(0, 0, "SensESP Sensor Data");
    
    // Analog input value
    display.drawString(0, 12, "Analog: " + String(current_analog_value, 2) + "V");
    
    // Digital input 1 (pin 5)
    String digital1_str = current_digital_input1 ? "HIGH" : "LOW";
    display.drawString(0, 24, "Digital1: " + digital1_str);
    
    // Digital input 2 (pin 4) 
    String digital2_str = current_digital_input2 ? "HIGH" : "LOW";
    display.drawString(0, 36, "Digital2: " + digital2_str);
    
    // Uptime
    display.drawString(0, 48, "Up: " + String(millis()/1000) + "s");
    
    // Signal K status
    display.setFont(ArialMT_Plain_10);
    display.setTextAlignment(TEXT_ALIGN_RIGHT);
    display.drawString(128, 54, "SignalK");
    
    display.display();
    
    // Also output to serial for debugging
    debugD("Display: Analog=%.2fV, D1=%s, D2=%s", 
           current_analog_value, 
           current_digital_input1 ? "HIGH" : "LOW",
           current_digital_input2 ? "HIGH" : "LOW");
  }
  
  delay(100);  // Small delay to prevent excessive CPU usage
}