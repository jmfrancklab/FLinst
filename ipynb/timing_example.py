%load_ext pyspecdata.ipy
import time

# here, I allocate my array

cap_axis = zeros(100)
all_my_blocks = []


# record the time at the start and start capturing

start_time = time.time()
for block in range(3):
    d = ndshape([100,2],['cap','t']).alloc()
    for n_scan in range(100):
        # here I would acctually capture and load into d
        d['cap',n_scan] = r_[1,2]*n_scan # just making data that differs from scan to scan
        time.sleep(0.01)
        cap_axis[n_scan] = time.time() - start_time
    d.labels('cap',cap_axis.copy()) # the need to "copy" capture axis was not expected
    # instead of adding to a list, we would save to a node
    all_my_blocks.append(d)
    time.sleep(0.2)

# look at the first block

all_my_blocks[0]

# and the second block

all_my_blocks[1]
