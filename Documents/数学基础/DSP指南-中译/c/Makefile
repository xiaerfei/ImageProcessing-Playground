CC      = cc
CFLAGS  = -std=c99 -O2 -Wall -Wextra
LDLIBS  = -lm

TARGETS = table2-1_mean_sd table2-2_running_stats \
          table2-3_histogram_stats table2-4_binned_histogram

all: $(TARGETS)

%: %.c
	$(CC) $(CFLAGS) -o $@ $< $(LDLIBS)

run: all
	@for t in $(TARGETS); do ./$$t; done

clean:
	rm -f $(TARGETS)

.PHONY: all run clean
