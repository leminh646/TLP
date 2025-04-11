# Copyright (c) 2023 The Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
system.clk_domain.clock = '4GHz'  # Increased clock speed
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
binary = 'tests/test-progs/hello/bin/riscv/linux/hello'
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

# Now we can modify the FloatSimdFU parameters
# Find the FloatSimdFU in the FU pool
fu_pool = system.cpu.executeFuncUnits
for i, fu in enumerate(fu_pool.funcUnits):
    # Check if this is the FloatSimdFU
    if hasattr(fu, 'opClasses') and any("Float" in op for op in fu.opClasses):
        print(f"Found FloatSimdFU at index {i}")
        print(f"Original opLat = {fu.opLat}, issueLat = {fu.issueLat}")
        
        # Modify the parameters
        fu.opLat = args.op_lat
        fu.issueLat = args.issue_lat
        
        print(f"Modified opLat = {fu.opLat}, issueLat = {fu.issueLat}")
        break

# Add debug print of all functional units
print("\nFunctional Units:")
for i, fu in enumerate(fu_pool.funcUnits):
    print(f"FU {i}: {type(fu).__name__}")
    print(f"  opLat: {fu.opLat}")
    print(f"  issueLat: {fu.issueLat}")
    print(f"  opClasses: {fu.opClasses}")

# Run the simulation with a reasonable tick count
print("\nStarting simulation...")
max_ticks = 10000000000  # 10 billion ticks (10 seconds at 4GHz)
exit_event = m5.simulate(max_ticks)

# Print results
print(f"\nExiting @ tick {m5.curTick()} because {exit_event.getCause()}")

print("\nSimulation complete!")
