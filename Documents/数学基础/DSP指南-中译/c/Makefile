CC      = cc
CFLAGS  = -std=c99 -O2 -Wall -Wextra
LDLIBS  = -lm

TARGETS = table2-1_mean_sd table2-2_running_stats \
          table2-3_histogram_stats table2-4_binned_histogram \
          table4-1_float_error table4-2_loop_control table4-5_add

all: $(TARGETS)

%: %.c
	$(CC) $(CFLAGS) -o $@ $< $(LDLIBS)

# 表 4-1 要在运行时切换舍入模式，必须告诉编译器别按默认舍入做优化
table4-1_float_error: CFLAGS += -frounding-math

run: all
	@for t in $(TARGETS); do ./$$t; done

clean:
	rm -f $(TARGETS)

.PHONY: all run clean
