#ifndef SRC_CHAIN_COUNTER_H_
#define SRC_CHAIN_COUNTER_H_

#include "sensesp.h"

#include <Arduino.h>

#include <memory>

#include "sensesp/sensors/sensor.h"
#include "sensesp/system/observablevalue.h"
#include "sensesp/ui/config_item.h"

namespace sensesp {

/**
 * @brief Windlass chain (rode) counter.
 *
 * Counts pulses from the gypsy sensor of a windlass (developed against a Quick
 * Eagle 1400 W) and turns them into deployed rode length. The sensor only
 * reports movement, not direction, so direction is taken from the up and down
 * contactor sense lines: while "up" is energized pulses subtract, while "down"
 * is energized they add. When neither line is energized the last known
 * direction is kept, which is the best that can be done with a single-channel
 * sensor -- a free-fall drop right after hauling will count in the wrong
 * direction until the down contactor is next used.
 *
 * The pin is polled and debounced in software rather than driven by an
 * interrupt. A windlass gypsy turns at a few revolutions per second at most, so
 * pulses are hundreds of milliseconds wide and a 5 ms poll has ample margin,
 * while the debounce window rejects contact bounce and contactor noise.
 *
 * The pulse count is persisted to the SensESP filesystem so the rode reading
 * survives a reboot. Writes are throttled: the count is flushed once movement
 * has settled, and at most every 30 s while the chain is running.
 *
 * @param sensor_pin GPIO connected to the gypsy sensor. Must be a
 * level-shifted or opto-isolated signal -- never the raw 12 V windlass
 * harness.
 *
 * @param up_pin GPIO connected to the "up"/haul contactor sense line.
 *
 * @param down_pin GPIO connected to the "down"/veer contactor sense line.
 *
 * @param distance_per_pulse Chain length per counted pulse, in meters.
 * Calibrate this; see README.
 *
 * @param config_path Configuration path for the web UI.
 */
class ChainCounter : public FloatSensor {
 public:
  ChainCounter(uint8_t sensor_pin, uint8_t up_pin, uint8_t down_pin,
               float distance_per_pulse = 0.1675,
               const String& config_path = "");

  virtual ~ChainCounter();

  /// Deployed rode in meters.
  float get_rode() const { return output_; }
  int get_pulse_count() const { return pulse_count_; }
  float get_distance_per_pulse() const { return distance_per_pulse_; }
  /// True while the haul (up) contactor is energized.
  bool get_up() const { return up_->get(); }
  /// True while the veer (down) contactor is energized.
  bool get_down() const { return down_->get(); }
  /// 1 while veering, -1 while hauling.
  int get_direction() const { return direction_; }

  /// Set the counter directly, e.g. to zero it with the anchor home.
  void set_pulse_count(int pulse_count);
  /// Set the counter from a rode length in meters.
  void set_rode(float rode_m);

  std::shared_ptr<ObservableValue<int>> pulse_count_output() {
    return pulse_count_out_;
  }
  std::shared_ptr<ObservableValue<bool>> up_output() { return up_; }
  std::shared_ptr<ObservableValue<bool>> down_output() { return down_; }

  bool to_json(JsonObject& root) override;
  bool from_json(const JsonObject& config) override;

 private:
  void update();
  void apply_pulse();
  void publish();
  bool read_direction_pin(uint8_t pin) const;

  const uint8_t sensor_pin_;
  const uint8_t up_pin_;
  const uint8_t down_pin_;

  // Configurable state.
  float distance_per_pulse_;
  int pulse_count_ = 0;
  bool count_both_edges_ = true;
  bool invert_direction_inputs_ = true;
  unsigned int debounce_ms_ = 15;

  // Runtime state.
  int direction_ = 1;  // Assume veering until a contactor says otherwise.
  bool stable_level_ = false;
  bool candidate_level_ = false;
  unsigned long candidate_since_ms_ = 0;
  unsigned long last_motion_ms_ = 0;
  unsigned long last_save_ms_ = 0;
  unsigned long last_publish_ms_ = 0;
  bool unsaved_pulses_ = false;

  std::shared_ptr<ObservableValue<int>> pulse_count_out_;
  std::shared_ptr<ObservableValue<bool>> up_;
  std::shared_ptr<ObservableValue<bool>> down_;

  reactesp::RepeatEvent* repeat_event_ = nullptr;
};

const String ConfigSchema(const ChainCounter& obj);

}  // namespace sensesp

#endif  // SRC_CHAIN_COUNTER_H_
