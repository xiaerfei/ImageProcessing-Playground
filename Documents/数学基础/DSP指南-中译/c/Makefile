CC      = cc
CFLAGS  = -std=c99 -O2 -Wall -Wextra
LDLIBS  = -lm

TARGETS = table2-1_mean_sd table2-2_running_stats \
          table2-3_histogram_stats table2-4_binned_histogram \
          table4-1_float_error table4-2_loop_control table4-5_add \
          table6-1_convolve_input_side table6-2_convolve_output_side \
          table7-1_difference_running_sum \
          table8-1_inverse_dft table8-2_dft_correlation \
          table8-3_rect_polar table8-4_phase_unwrap

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
