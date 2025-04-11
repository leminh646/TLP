"""
Simple FloatSimdFU Test

This script directly modifies the FloatSimdFU parameters in a MinorCPU configuration
to test a specific combination of opLat and issueLat.

Usage:
    python simple_float_simd_test.py --op-lat=N --issue-lat=M
"""

import argparse
import sys

import m5
from m5.objects import *
from m5.util import addToPath

# Parse command line arguments
parser = argparse.ArgumentParser(description='Simple FloatSimdFU Test')
parser.add_argument('--op-lat', type=int, default=3, help='Operation latency')
parser.add_argument('--issue-lat', type=int, default=4, help='Issue latency')
args = parser.parse_args()

# Print configuration
print(f"\nRunning with FloatSimdFU configuration:")
print(f"  opLat = {args.op_lat}")
print(f"  issueLat = {args.issue_lat}")
print(f"  Total latency = {args.op_lat + args.issue_lat} cycles\n")

# Create a system
system = System()

# Set up the clock domain
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = '2GHz'  # Increased clock speed
system.clk_domain.voltage_domain = VoltageDomain()

# Set up the memory system
system.mem_mode = 'timing'
system.mem_ranges = [AddrRange('32MB')]  # Reduced memory size

# Create a CPU
system.cpu = MinorCPU()
system.cpu.createInterruptController()

# Create a memory bus
system.membus = SystemXBar()

# Connect the CPU ports to the membus
system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports

# Create a memory controller
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

# Create a process to run
binary = 'tests/test-progs/float_workload'
system.workload = SEWorkload.init_compatible(binary)

process = Process()
process.cmd = [binary]
system.cpu.workload = process
system.cpu.createThreads()


# Define a custom functional unit pool
system.cpu.executeFuncUnits = MinorFUPool()
system.cpu.executeFuncUnits.funcUnits = [
    MinorDefaultIntFU(),
    MinorDefaultIntMulFU(),
    MinorDefaultIntDivFU(),
    MinorDefaultMemFU(),
    # Now include custom FloatSimdFUs with tunable latency
    MinorDefaultFloatSimdFU(opLat=args.op_lat, issueLat=args.issue_lat),
    MinorDefaultFloatSimdFU(opLat=args.op_lat, issueLat=args.issue_lat),
    MinorDefaultFloatSimdFU(opLat=args.op_lat, issueLat=args.issue_lat),
]


# Create the root
root = Root(full_system=False, system=system)

# Instantiate the simulation
m5.instantiate()


# Run the simulation with a reasonable tick count
print("\nStarting simulation...")
max_ticks = 10000000000  
exit_event = m5.simulate(max_ticks)

# Print results
print(f"\nExiting @ tick {m5.curTick()} because {exit_event.getCause()}")

print("\nSimulation complete!")
