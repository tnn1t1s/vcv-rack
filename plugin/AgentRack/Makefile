RACK_DIR := ../../vendor/rack-sdk

SOURCES += src/plugin.cpp
SOURCES += src/Attenuate.cpp
SOURCES += src/ADSR.cpp
SOURCES += src/Crinkle.cpp
SOURCES += src/Inspector.cpp
SOURCES += src/Ladder.cpp
SOURCES += src/FFTProvider.cpp
SOURCES += src/FFTvDSP.cpp
SOURCES += src/Noise.cpp
SOURCES += src/Saphire.cpp
SOURCES += src/Sonic.cpp

LDFLAGS += -framework Accelerate

RACK_LIB := /Applications/VCV Rack 2 Pro.app/Contents/Resources

FLAGS += -I/opt/homebrew/include

DISTRIBUTABLES += res

# Link against the real libRack so the plugin has a valid engine at load time
LDFLAGS += -L"$(RACK_LIB)"

include $(RACK_DIR)/plugin.mk
