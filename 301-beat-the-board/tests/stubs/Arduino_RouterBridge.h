#pragma once
struct BridgeClass {
  void begin() {}
  template <typename F> void provide_safe(const char *, F) {}
};
inline BridgeClass Bridge;
