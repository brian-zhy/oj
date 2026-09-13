# 构建 no_opt_pragma.so
#
# 关键要求：本 Makefile 使用的 g++ 必须与“评测时实际调用的编译器”是同一个
# 版本，因为插件头文件来自 `g++ -print-file-name=plugin`。
#
# Debian/Ubuntu (GCC 14):
#   sudo apt install g++-14 gcc-14-plugin-dev
#   make CXX=g++-14
#
# 若评测用的是系统默认 g++，直接 `make` 即可。

CXX      ?= g++
PLUGIN_INC := $(shell $(CXX) -print-file-name=plugin)/include
CXXFLAGS ?= -O2 -fPIC -fno-rtti -Wall -Wextra
TARGET   := no_opt_pragma.so

all: $(TARGET)

$(TARGET): no_opt_pragma.cc
	@echo "==> 使用插件头文件目录: $(PLUGIN_INC)"
	$(CXX) -shared $(CXXFLAGS) -I$(PLUGIN_INC) -o $@ $<

clean:
	rm -f $(TARGET)

.PHONY: all clean
