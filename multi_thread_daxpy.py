#!/usr/bin/env python3

import argparse
import sys
import m5
from m5.objects import *
from m5.util import addToPath

# Parse command line arguments
parser = argparse.ArgumentParser(description='Multi-threaded DAXPY simulation')
parser.add_argument('--num-cores', type=int, default=4, help='Number of CPU cores')
parser.add_argument('--vector-size', type=int, default=1000000, help='Size of input vectors')
args = parser.parse_args()

# Create a system
system = System()

# Set up the clock domain
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = '3GHz'
system.clk_domain.voltage_domain = VoltageDomain()

# Set up the memory system
system.mem_mode = 'timing'
system.mem_ranges = [AddrRange('4GB')]

# Create a CPU with multiple cores
system.cpu = [MinorCPU(cpu_id=i) for i in range(args.num_cores)]
for cpu in system.cpu:
    cpu.createInterruptController()

# Create a memory bus
system.membus = SystemXBar()

# Connect CPU ports to the membus
for cpu in system.cpu:
    cpu.icache_port = system.membus.cpu_side_ports
    cpu.dcache_port = system.membus.cpu_side_ports

# Create a memory controller
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

# Create a process for each core
binary = 'tests/test-progs/multi_thread_daxpy'
system.workload = SEWorkload.init_compatible(binary)

process = Process()
process.cmd = [binary, str(args.vector_size)]

# Assign the process to all cores
for cpu in system.cpu:
    cpu.workload = process
    cpu.createThreads()

# Create the root
root = Root(full_system=False, system=system)

# Instantiate the simulation
m5.instantiate()

# Run the simulation
print("\nStarting simulation...")
max_ticks = 10000000000  # 10 billion ticks
exit_event = m5.simulate(max_ticks)

# Print results
print(f"\nExiting @ tick {m5.curTick()} because {exit_event.getCause()}")

print("\nSimulation complete!")
