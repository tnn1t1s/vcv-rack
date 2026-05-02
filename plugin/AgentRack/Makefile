RACK_DIR  := ../../vendor/rack-sdk
LLAMA_DIR := ../../vendor/llama.cpp

SOURCES += src/plugin.cpp
SOURCES += src/Attenuate.cpp
SOURCES += src/ADSR.cpp
SOURCES += src/Crinkle.cpp
SOURCES += src/Ladder.cpp
SOURCES += src/FFTProvider.cpp
SOURCES += src/FFTvDSP.cpp
SOURCES += src/LoopPackShared.cpp
SOURCES += src/Cassette.cpp
SOURCES += src/Noise.cpp
SOURCES += src/Saphire.cpp
SOURCES += src/Sonic.cpp
SOURCES += src/Steel.cpp
SOURCES += src/BusCrush.cpp
SOURCES += src/ClockDiv.cpp
SOURCES += src/Tonnetz.cpp
SOURCES += src/Maurizio.cpp
SOURCES += src/Kck.cpp
SOURCES += src/Toms.cpp
SOURCES += src/Chh.cpp
SOURCES += src/Ohh.cpp
SOURCES += src/CrashRide.cpp
SOURCES += src/RimClap.cpp
SOURCES += src/Snr.cpp
SOURCES += src/Tr909Ctrl.cpp

LDFLAGS += -framework Accelerate
LDFLAGS += -L/opt/homebrew/lib -lsndfile

RACK_LIB := /Applications/VCV Rack 2 Pro.app/Contents/Resources

FLAGS += -I/opt/homebrew/include
FLAGS += -I$(LLAMA_DIR)/build/include

LDFLAGS += -L$(LLAMA_DIR)/build -lllama_full
LDFLAGS += -framework Metal -framework Foundation

DISTRIBUTABLES += res

# Link against the real libRack so the plugin has a valid engine at load time
LDFLAGS += -L"$(RACK_LIB)"

include $(RACK_DIR)/plugin.mk

RACK_PLUGINS := $(HOME)/Library/Application Support/Rack2/plugins-mac-arm64

install: all
	cp plugin.dylib "$(RACK_PLUGINS)/AgentRack/plugin.dylib"
	cp plugin.json  "$(RACK_PLUGINS)/AgentRack/plugin.json"
	cp -r res/      "$(RACK_PLUGINS)/AgentRack/res/"
	@if [ -d presets ]; then cp -r presets "$(RACK_PLUGINS)/AgentRack/"; fi
