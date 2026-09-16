#include "sensesp.h"

#include "chain_counter.h"

#include <cmath>

#include "sensesp_base_app.h"

namespace sensesp {

// How often the sensor pin is sampled. Pulses from a windlass gypsy are
// hundreds of ms wide, so this is comfortably oversampled.
constexpr unsigned int kPollIntervalMs = 5;
// Emit a value at least this often even if nothing is moving, so the Signal K
// server keeps a fresh timestamp on the path.
constexpr unsigned long kHeartbeatMs = 5000;
// Flush the pulse count once the chain has been still for this long.
constexpr unsigned long kSaveSettleMs = 2000;
// ...and at most this often while it is still running.
constexpr unsigned long kSaveMaxIntervalMs = 30000;

ChainCounter::ChainCounter(uint8_t sensor_pin, uint8_t up_pin, uint8_t down_pin,
                           float distance_per_pulse, const String& config_path)
    : FloatSensor(config_path),
      sensor_pin_{sensor_pin},
      up_pin_{up_pin},
      down_pin_{down_pin},
      distance_per_pulse_{distance_per_pulse} {
  pinMode(sensor_pin_, INPUT_PULLUP);
  pinMode(up_pin_, INPUT_PULLUP);
  pinMode(down_pin_, INPUT_PULLUP);

  pulse_count_out_ = std::make_shared<ObservableValue<int>>(0);
  up_ = std::make_shared<ObservableValue<bool>>(false);
  down_ = std::make_shared<ObservableValue<bool>>(false);

  // Called here rather than in a base constructor: only now is the dynamic
  // type complete, so from_json() dispatches to this class's override.
  load();

  output_ = pulse_count_ * distance_per_pulse_;
  pulse_count_out_->set(pulse_count_);

  // Seed the edge detector from the current pin state so booting with the
  // sensor asserted doesn't count a phantom pulse.
  stable_level_ = digitalRead(sensor_pin_);
  candidate_level_ = stable_level_;
  candidate_since_ms_ = millis();
  last_save_ms_ = millis();

  repeat_event_ =
      event_loop()->onRepeat(kPollIntervalMs, [this]() { this->update(); });
}

ChainCounter::~ChainCounter() {
  if (repeat_event_ != nullptr) {
    repeat_event_->remove(event_loop());
  }
}

bool ChainCounter::read_direction_pin(uint8_t pin) const {
  const bool level = digitalRead(pin);
  return invert_direction_inputs_ ? !level : level;
}

void ChainCounter::update() {
  const unsigned long now = millis();

  // Latch direction from the contactor sense lines. If both are energized
  // something is wired wrong; keep the previous direction rather than guess.
  const bool up = read_direction_pin(up_pin_);
  const bool down = read_direction_pin(down_pin_);
  if (up != up_->get()) {
    up_->set(up);
  }
  if (down != down_->get()) {
    down_->set(down);
  }
  if (up && !down) {
    direction_ = -1;
  } else if (down && !up) {
    direction_ = 1;
  }

  // Debounced edge detection on the gypsy sensor.
  const bool level = digitalRead(sensor_pin_);
  if (level != candidate_level_) {
    candidate_level_ = level;
    candidate_since_ms_ = now;
  } else if (candidate_level_ != stable_level_ &&
             now - candidate_since_ms_ >= debounce_ms_) {
    stable_level_ = candidate_level_;
    if (count_both_edges_ || stable_level_) {
      apply_pulse();
    }
  }

  publish();

  // Persist the count, throttled to spare the flash.
  if (unsaved_pulses_ && (now - last_motion_ms_ >= kSaveSettleMs ||
                          now - last_save_ms_ >= kSaveMaxIntervalMs)) {
    save();
    unsaved_pulses_ = false;
    last_save_ms_ = now;
  }
}

void ChainCounter::apply_pulse() {
  pulse_count_ += direction_;
  // The rode can't be shorter than nothing; hauling past zero just means the
  // counter had drifted high.
  if (pulse_count_ < 0) {
    pulse_count_ = 0;
  }
  unsaved_pulses_ = true;
  last_motion_ms_ = millis();
}

void ChainCounter::publish() {
  const unsigned long now = millis();
  const float rode = pulse_count_ * distance_per_pulse_;
  if (rode != output_ || now - last_publish_ms_ >= kHeartbeatMs) {
    last_publish_ms_ = now;
    if (pulse_count_ != pulse_count_out_->get()) {
      pulse_count_out_->set(pulse_count_);
    }
    this->emit(rode);
  }
}

void ChainCounter::set_pulse_count(int pulse_count) {
  pulse_count_ = pulse_count < 0 ? 0 : pulse_count;
  unsaved_pulses_ = false;
  save();
  last_save_ms_ = millis();
  pulse_count_out_->set(pulse_count_);
  this->emit(pulse_count_ * distance_per_pulse_);
}

void ChainCounter::set_rode(float rode_m) {
  if (distance_per_pulse_ <= 0) {
    ESP_LOGW(__FILENAME__, "Distance per pulse is not set; ignoring rode %.2f",
             rode_m);
    return;
  }
  set_pulse_count(static_cast<int>(std::lroundf(rode_m / distance_per_pulse_)));
}

bool ChainCounter::to_json(JsonObject& root) {
  root["distance_per_pulse"] = distance_per_pulse_;
  root["pulse_count"] = pulse_count_;
  root["count_both_edges"] = count_both_edges_;
  root["invert_direction_inputs"] = invert_direction_inputs_;
  root["debounce_ms"] = debounce_ms_;
  return true;
}

bool ChainCounter::from_json(const JsonObject& config) {
  // Every key is optional: a config file written by an older build, or a
  // partial edit in the web UI, should not throw away the whole object.
  if (config["distance_per_pulse"].is<float>()) {
    distance_per_pulse_ = config["distance_per_pulse"];
  }
  if (config["pulse_count"].is<int>()) {
    pulse_count_ = config["pulse_count"];
    if (pulse_count_ < 0) {
      pulse_count_ = 0;
    }
  }
  if (config["count_both_edges"].is<bool>()) {
    count_both_edges_ = config["count_both_edges"];
  }
  if (config["invert_direction_inputs"].is<bool>()) {
    invert_direction_inputs_ = config["invert_direction_inputs"];
  }
  if (config["debounce_ms"].is<unsigned int>()) {
    debounce_ms_ = config["debounce_ms"];
  }

  output_ = pulse_count_ * distance_per_pulse_;
  if (pulse_count_out_ != nullptr) {
    pulse_count_out_->set(pulse_count_);
  }
  return true;
}

const String ConfigSchema(const ChainCounter& obj) {
  return R"###({"type":"object","properties":{
"distance_per_pulse":{"title":"Distance per pulse (m)","type":"number","description":"Chain length paid out per counted pulse. Measure it: mark the chain, veer to the mark, divide the marked length by the pulse count."},
"pulse_count":{"title":"Pulse count","type":"number","description":"Current counter value. Set to 0 with the anchor fully home."},
"count_both_edges":{"title":"Count both edges","type":"boolean","description":"Count rising and falling edges of the gypsy sensor. Halving this doubles the distance per pulse."},
"invert_direction_inputs":{"title":"Invert up/down inputs","type":"boolean","description":"Treat the up and down contactor sense lines as active low."},
"debounce_ms":{"title":"Debounce (ms)","type":"number","description":"A sensor edge must be stable for this long before it is counted."}
}})###";
}

}  // namespace sensesp
