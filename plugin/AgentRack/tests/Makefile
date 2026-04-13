CXX      := c++
CXXFLAGS := -std=c++11 -stdlib=libc++ -O2 -I.. -I../src
LDFLAGS  := -framework Accelerate

FFT_SRCS := test_fft.cpp ../src/FFTProvider.cpp ../src/FFTvDSP.cpp
FFT_BIN  := test_fft
CV_SRCS  := test_signal_cv.cpp
CV_BIN   := test_signal_cv

all: $(FFT_BIN) $(CV_BIN)

$(FFT_BIN): $(FFT_SRCS)
	$(CXX) $(CXXFLAGS) $(FFT_SRCS) $(LDFLAGS) -o $(FFT_BIN)

$(CV_BIN): $(CV_SRCS)
	$(CXX) $(CXXFLAGS) $(CV_SRCS) -o $(CV_BIN)

run: $(FFT_BIN)
	./$(FFT_BIN)

run-cv: $(CV_BIN)
	./$(CV_BIN)

clean:
	rm -f $(FFT_BIN) $(CV_BIN)

.PHONY: all run run-cv clean
