CXX      := c++
CXXFLAGS := -std=c++11 -stdlib=libc++ -O2 -I.. -I../src -I../../../vendor/rack-sdk/include -I../../../vendor/rack-sdk/dep/include
LDFLAGS  := -framework Accelerate
RACK_LIB_DIR := ../../../vendor/rack-sdk
RACK_LDFLAGS := -L$(RACK_LIB_DIR) -lRack
BUILD_DIR := build

FFT_SRCS := test_fft.cpp ../src/FFTProvider.cpp ../src/FFTvDSP.cpp
FFT_BIN  := $(BUILD_DIR)/test_fft
CV_SRCS  := test_signal_cv.cpp
CV_BIN   := $(BUILD_DIR)/test_signal_cv
AUDIO_SRCS := test_signal_audio.cpp
AUDIO_BIN  := $(BUILD_DIR)/test_signal_audio
PCONV_SRCS := test_partitioned_convolution.cpp
PCONV_BIN  := $(BUILD_DIR)/test_partitioned_convolution
CONTRACT_SRCS := test_component_contracts.cpp
CONTRACT_BIN  := $(BUILD_DIR)/test_component_contracts
MODULE_SRCS := test_module_regressions.cpp
MODULE_BIN  := $(BUILD_DIR)/test_module_regressions
MODULE_HEADERS := ModuleHarness.hpp \
	../src/Attenuate.cpp \
	../src/ADSR.cpp \
	../src/ClockDiv.cpp \
	../src/Noise.cpp \
	../src/Crinkle.cpp \
	../src/Ladder.cpp \
	../src/Sonic.cpp \
	../src/Maurizio.cpp \
	../src/Tonnetz.cpp \
	../src/Kck.cpp \
	../src/Snr.cpp \
	../src/Toms.cpp \
	../src/Chh.cpp \
	../src/Ohh.cpp \
	../src/RimClap.cpp \
	../src/CrashRide.cpp
CASSETTE_RT_SRCS := test_cassette_runtime.cpp
CASSETTE_RT_BIN  := $(BUILD_DIR)/test_cassette_runtime
CASSETTE_PROFILE_SRCS := test_cassette_machine_profile.cpp
CASSETTE_PROFILE_BIN  := $(BUILD_DIR)/test_cassette_machine_profile
SAPHIRE_RT_SRCS := test_saphire_runtime.cpp
SAPHIRE_RT_BIN  := $(BUILD_DIR)/test_saphire_runtime
SAPHIRE_IR_SRCS := test_saphire_impulse_response.cpp
SAPHIRE_IR_BIN  := $(BUILD_DIR)/test_saphire_impulse_response
SAPHIRE_WET_SRCS := test_saphire_wet_path.cpp
SAPHIRE_WET_BIN  := $(BUILD_DIR)/test_saphire_wet_path
VOICE_LAB_COMMON_SRCS := ../src/FFTProvider.cpp ../src/FFTvDSP.cpp
VOICE_LAB_HEADERS := voice_lab_common.hpp voice_lab_render_support.hpp \
	../src/Kck.cpp \
	../src/Snr.cpp \
	../src/Toms.cpp \
	../src/Chh.cpp \
	../src/Ohh.cpp \
	../src/RimClap.cpp \
	../src/CrashRide.cpp
VOICE_LAB_ANALYZE_SRCS := voice_lab_analyze.cpp $(VOICE_LAB_COMMON_SRCS)
VOICE_LAB_ANALYZE_BIN  := $(BUILD_DIR)/ar-analyze
VOICE_LAB_RENDER_SRCS := voice_lab_render.cpp $(VOICE_LAB_COMMON_SRCS)
VOICE_LAB_RENDER_BIN  := $(BUILD_DIR)/ar-render
VOICE_LAB_COMPARE_SRCS := voice_lab_compare.cpp $(VOICE_LAB_COMMON_SRCS)
VOICE_LAB_COMPARE_BIN  := $(BUILD_DIR)/ar-compare

all: $(FFT_BIN) $(CV_BIN) $(AUDIO_BIN) $(PCONV_BIN) $(CONTRACT_BIN) $(MODULE_BIN) $(CASSETTE_RT_BIN) $(CASSETTE_PROFILE_BIN) $(SAPHIRE_RT_BIN) $(SAPHIRE_IR_BIN) $(SAPHIRE_WET_BIN) $(VOICE_LAB_ANALYZE_BIN) $(VOICE_LAB_RENDER_BIN) $(VOICE_LAB_COMPARE_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(FFT_BIN): $(FFT_SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(FFT_SRCS) $(LDFLAGS) -o $(FFT_BIN)

$(CV_BIN): $(CV_SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(CV_SRCS) -o $(CV_BIN)

$(AUDIO_BIN): $(AUDIO_SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(AUDIO_SRCS) -o $(AUDIO_BIN)

$(PCONV_BIN): $(PCONV_SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(PCONV_SRCS) $(LDFLAGS) -o $(PCONV_BIN)

$(CONTRACT_BIN): $(CONTRACT_SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(CONTRACT_SRCS) -o $(CONTRACT_BIN)

$(MODULE_BIN): $(MODULE_SRCS) $(MODULE_HEADERS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(MODULE_SRCS) $(LDFLAGS) $(RACK_LDFLAGS) -o $(MODULE_BIN)

$(CASSETTE_RT_BIN): $(CASSETTE_RT_SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(CASSETTE_RT_SRCS) $(LDFLAGS) -o $(CASSETTE_RT_BIN)

$(CASSETTE_PROFILE_BIN): $(CASSETTE_PROFILE_SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(CASSETTE_PROFILE_SRCS) $(LDFLAGS) -o $(CASSETTE_PROFILE_BIN)

$(SAPHIRE_RT_BIN): $(SAPHIRE_RT_SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(SAPHIRE_RT_SRCS) $(LDFLAGS) -o $(SAPHIRE_RT_BIN)

$(SAPHIRE_IR_BIN): $(SAPHIRE_IR_SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(SAPHIRE_IR_SRCS) $(LDFLAGS) -o $(SAPHIRE_IR_BIN)

$(SAPHIRE_WET_BIN): $(SAPHIRE_WET_SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(SAPHIRE_WET_SRCS) $(LDFLAGS) -o $(SAPHIRE_WET_BIN)

$(VOICE_LAB_ANALYZE_BIN): $(VOICE_LAB_ANALYZE_SRCS) voice_lab_common.hpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(VOICE_LAB_ANALYZE_SRCS) $(LDFLAGS) -o $(VOICE_LAB_ANALYZE_BIN)

$(VOICE_LAB_RENDER_BIN): $(VOICE_LAB_RENDER_SRCS) $(VOICE_LAB_HEADERS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(VOICE_LAB_RENDER_SRCS) $(LDFLAGS) $(RACK_LDFLAGS) -o $(VOICE_LAB_RENDER_BIN)

$(VOICE_LAB_COMPARE_BIN): $(VOICE_LAB_COMPARE_SRCS) $(VOICE_LAB_HEADERS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(VOICE_LAB_COMPARE_SRCS) $(LDFLAGS) $(RACK_LDFLAGS) -o $(VOICE_LAB_COMPARE_BIN)

run: $(FFT_BIN)
	./$(FFT_BIN)

run-cv: $(CV_BIN)
	./$(CV_BIN)

run-audio: $(AUDIO_BIN)
	./$(AUDIO_BIN)

run-pconv: $(PCONV_BIN)
	./$(PCONV_BIN)

run-contracts: $(CONTRACT_BIN)
	./$(CONTRACT_BIN)

run-modules: $(MODULE_BIN)
	DYLD_LIBRARY_PATH=$(RACK_LIB_DIR) ./$(MODULE_BIN)

run-cassette-runtime: $(CASSETTE_RT_BIN)
	./$(CASSETTE_RT_BIN)

run-cassette-profile: $(CASSETTE_PROFILE_BIN)
	./$(CASSETTE_PROFILE_BIN)

run-saphire-runtime: $(SAPHIRE_RT_BIN)
	./$(SAPHIRE_RT_BIN)

run-saphire-ir: $(SAPHIRE_IR_BIN)
	./$(SAPHIRE_IR_BIN)

run-saphire-wet: $(SAPHIRE_WET_BIN)
	./$(SAPHIRE_WET_BIN)

run-ar-analyze: $(VOICE_LAB_ANALYZE_BIN)
	./$(VOICE_LAB_ANALYZE_BIN)

run-ar-render: $(VOICE_LAB_RENDER_BIN)
	DYLD_LIBRARY_PATH=$(RACK_LIB_DIR) ./$(VOICE_LAB_RENDER_BIN)

run-ar-compare: $(VOICE_LAB_COMPARE_BIN)
	DYLD_LIBRARY_PATH=$(RACK_LIB_DIR) ./$(VOICE_LAB_COMPARE_BIN)

run-all: all
	./$(FFT_BIN)
	./$(CV_BIN)
	./$(AUDIO_BIN)
	./$(PCONV_BIN)
	./$(CONTRACT_BIN)
	DYLD_LIBRARY_PATH=$(RACK_LIB_DIR) ./$(MODULE_BIN)
	./$(CASSETTE_RT_BIN)
	./$(CASSETTE_PROFILE_BIN)
	./$(SAPHIRE_RT_BIN)
	./$(SAPHIRE_IR_BIN)
	./$(SAPHIRE_WET_BIN)

clean:
	rm -rf $(BUILD_DIR)

.PHONY: all run run-cv run-audio run-pconv run-contracts run-modules run-cassette-runtime run-cassette-profile run-saphire-runtime run-saphire-ir run-saphire-wet run-ar-analyze run-ar-render run-ar-compare run-all clean
