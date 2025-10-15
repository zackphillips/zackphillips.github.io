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
    
    // Title
    display.drawString(0, 0, "SensESP Engine Reader");
    
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
    debugD("Display: A%d=%.2fV, A%d=%.2fV, A%d=%.2fV, D%d=%s, D%d=%s", 
           kAnalogInput1Gpio, current_analog_value1,
           kAnalogInput2Gpio, current_analog_value2, 
           kAnalogInput3Gpio, current_analog_value3,
           kDigitalInput1Gpio, current_digital_input1 ? "HIGH" : "LOW",
           kDigitalInput2Gpio, current_digital_input2 ? "HIGH" : "LOW");
  }
  
  delay(100);  // Small delay to prevent excessive CPU usage
}

