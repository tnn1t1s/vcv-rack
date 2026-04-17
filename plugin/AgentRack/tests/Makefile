CXX      := c++
CXXFLAGS := -std=c++11 -stdlib=libc++ -O2 -I.. -I../src -I../../../vendor/rack-sdk/include -I../../../vendor/rack-sdk/dep/include
LDFLAGS  := -framework Accelerate
RACK_LIB_DIR := ../../../vendor/rack-sdk
RACK_LDFLAGS := -L$(RACK_LIB_DIR) -lRack

FFT_SRCS := test_fft.cpp ../src/FFTProvider.cpp ../src/FFTvDSP.cpp
FFT_BIN  := test_fft
CV_SRCS  := test_signal_cv.cpp
CV_BIN   := test_signal_cv
AUDIO_SRCS := test_signal_audio.cpp
AUDIO_BIN  := test_signal_audio
PCONV_SRCS := test_partitioned_convolution.cpp
PCONV_BIN  := test_partitioned_convolution
CONTRACT_SRCS := test_component_contracts.cpp
CONTRACT_BIN  := test_component_contracts
MODULE_SRCS := test_module_regressions.cpp
MODULE_BIN  := test_module_regressions
CASSETTE_RT_SRCS := test_cassette_runtime.cpp
CASSETTE_RT_BIN  := test_cassette_runtime

all: $(FFT_BIN) $(CV_BIN) $(AUDIO_BIN) $(PCONV_BIN) $(CONTRACT_BIN) $(MODULE_BIN) $(CASSETTE_RT_BIN)

$(FFT_BIN): $(FFT_SRCS)
	$(CXX) $(CXXFLAGS) $(FFT_SRCS) $(LDFLAGS) -o $(FFT_BIN)

$(CV_BIN): $(CV_SRCS)
	$(CXX) $(CXXFLAGS) $(CV_SRCS) -o $(CV_BIN)

$(AUDIO_BIN): $(AUDIO_SRCS)
	$(CXX) $(CXXFLAGS) $(AUDIO_SRCS) -o $(AUDIO_BIN)

$(PCONV_BIN): $(PCONV_SRCS)
	$(CXX) $(CXXFLAGS) $(PCONV_SRCS) $(LDFLAGS) -o $(PCONV_BIN)

$(CONTRACT_BIN): $(CONTRACT_SRCS)
	$(CXX) $(CXXFLAGS) $(CONTRACT_SRCS) -o $(CONTRACT_BIN)

$(MODULE_BIN): $(MODULE_SRCS)
	$(CXX) $(CXXFLAGS) $(MODULE_SRCS) $(LDFLAGS) $(RACK_LDFLAGS) -o $(MODULE_BIN)

$(CASSETTE_RT_BIN): $(CASSETTE_RT_SRCS)
	$(CXX) $(CXXFLAGS) $(CASSETTE_RT_SRCS) $(LDFLAGS) -o $(CASSETTE_RT_BIN)

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

run-all: all
	./$(FFT_BIN)
	./$(CV_BIN)
	./$(AUDIO_BIN)
	./$(PCONV_BIN)
	./$(CONTRACT_BIN)
	DYLD_LIBRARY_PATH=$(RACK_LIB_DIR) ./$(MODULE_BIN)
	./$(CASSETTE_RT_BIN)

clean:
	rm -f $(FFT_BIN) $(CV_BIN) $(AUDIO_BIN) $(PCONV_BIN) $(CONTRACT_BIN) $(MODULE_BIN) $(CASSETTE_RT_BIN)

.PHONY: all run run-cv run-audio run-pconv run-contracts run-modules run-cassette-runtime run-all clean
