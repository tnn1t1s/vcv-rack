CXX      := c++
CXXFLAGS := -std=c++11 -stdlib=libc++ -O2 -I.. -I../src
LDFLAGS  := -framework Accelerate

SRCS := test_fft.cpp ../src/FFTProvider.cpp ../src/FFTvDSP.cpp
BIN  := test_fft

all: $(BIN)

$(BIN): $(SRCS)
	$(CXX) $(CXXFLAGS) $(SRCS) $(LDFLAGS) -o $(BIN)

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)

.PHONY: all run clean
